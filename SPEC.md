# Lumen — Improvement Spec

A prioritized roadmap of improvements across three axes: **agent quality** (better lessons), **production readiness** (ship it), and **new features** (expand capability). Items are ordered within each section by impact, not effort.

---

## Index

### Agent quality
1. [Few-shot examples in narrative + scene prompts](#aq1)
2. [Cross-scene continuity via shared LessonContext](#aq2)
3. [Self-critique pass before rendering](#aq3)
4. [Per-render cost + latency tracking](#aq4)
5. [Render-failure retry with error feedback](#aq5)
6. [Tool-call static validation](#aq6)
7. [Camera movement tools](#aq7)
8. [Synced TTS narration baked into video](#aq8)
9. [Variable pacing + insight emphasis](#aq9)
10. [Adaptive lesson length + complexity](#aq10)
11. [Streaming narrative plan to UI](#aq11)
12. [Narrative style presets](#aq12)

### Production readiness
13. [Persistent job state in Postgres](#pr1)
14. [Redis + RQ job queue with separate workers](#pr2)
15. [Object storage (S3 / R2) for videos](#pr3)
16. [Production WSGI + Docker Compose](#pr4)
17. [User accounts and auth](#pr5)
18. [Rate limiting and quotas](#pr6)
19. [CI/CD via GitHub Actions](#pr7)
20. [Sentry error tracking (front + back)](#pr8)
21. [OpenAPI schema → typed frontend client](#pr9)
22. [Secrets management + env separation](#pr10)
23. [CDN in front of /media/ + cache headers](#pr11)
24. [Performance + bundle-size budgets in CI](#pr12)

### New features
25. [PWA install + offline shell](#nf1)
26. [Multi-language code editor (JS, C++)](#nf2)
27. [Compare user solution to optimal in-browser](#nf3)
28. [Spaced repetition for saved videos](#nf4)
29. [Lesson playlists / courses](#nf5)
30. [Real-time collaborative notes](#nf6)
31. [Public lesson library + discovery](#nf7)
32. [Embed widget (single-lesson iframe)](#nf8)
33. [Voice input via browser Whisper](#nf9)
34. [Adaptive difficulty driven by quiz history](#nf10)
35. [Topic prerequisite graph](#nf11)
36. [Export lessons as PDF or MP4 download](#nf12)

---

## Agent quality

### <a id="aq1"></a>1. Few-shot examples in narrative + scene prompts
The biggest single quality lever. Right now the prompts describe the rules in prose; LLMs follow examples 10× more reliably than rules. Add 2–3 hand-crafted "golden" lessons (e.g. two-pointer palindrome, Kadane's, Riemann sum) directly into the system prompt so the model has a target to mimic. Same idea for `build_scene`: show one example tool-call sequence that hits all the quality rules (one `emphasize`, one `pause(2)`, one `show_result`, ≤3 elements). Affects `agent/lesson_director.py` only. Effort: 2–3 hours of careful curation.

### <a id="aq2"></a>2. Cross-scene continuity via shared LessonContext
Today each scene starts cold. Beautiful lessons carry visual elements across — the array from scene 1 should still be on screen when scene 2 explains the invariant. Introduce a `LessonContext` object passed between `build_scene` calls: list of element IDs created so far, descriptions, last-known position. The scene-2 LLM call sees "scene 1 ended with element_id `arr` (an ArrayStrip of `[3,1,4,1,5,9,2,6]`) at center" and can reference it directly. Implementation: `ToolExecutor` already maintains element state — just plumb context strings into the scene prompts. Touches `lesson_director.py` and `tool_executor.py`. Effort: 1 day.

### <a id="aq3"></a>3. Self-critique pass before rendering
After `build_scene` produces tool calls, run one more LLM pass: "Here are the tool calls. Does this scene have one clear insight, an `emphasize` at that moment, no static stretches, ≤3 elements? If not, fix it." Catches the most common LLM laziness (boring scenes with no emphasis, too many elements, missing result_box). Adds ~3s per scene, but the quality jump justifies it. Make it a separate function `critique_scene(tool_calls, scene_plan)` returning revised calls. Effort: half day.

### <a id="aq4"></a>4. Per-render cost + latency tracking
Currently no visibility into LLM spend or per-stage timing. Add a `RenderTrace` object that accumulates: model used, prompt+completion tokens, ms elapsed per stage. Persist to `media/traces/{job_id}.json` and expose at `GET /api/trace/<job_id>`. UI: collapsible "Behind the scenes" panel on the rendered video showing cost and timing breakdown. Critical for understanding which scenes are expensive. Effort: half day plus a tiny UI panel.

### <a id="aq5"></a>5. Render-failure retry with error feedback
Today if a scene's tool calls produce a broken Manim scene (e.g., wrong index, missing element), the scene just renders weirdly or partially. Wrap `_run_render` so on subprocess error, the agent gets `(scene_plan, tool_calls, manim_stderr)` and retries `build_scene` with a "the previous attempt failed because…" prefix. One retry covers ~80% of failures. Effort: 3 hours.

### <a id="aq6"></a>6. Tool-call static validation
Before executing, walk the tool-call list checking: every `element_id` referenced in `move_pointer`, `highlight_cells`, `set_hashmap_entry`, etc. exists from a prior `show_*` call. Flag forward references and orphan pointers. Reject the scene and retry rather than silently skipping at runtime. Lives in `tool_executor.py` or a new `tool_linter.py`. Effort: 3 hours.

### <a id="aq7"></a>7. Camera movement tools
Add `pan_to(element_id)`, `zoom_to(element_id, level)`, `zoom_out()` as new tools. Manim supports `self.camera.frame.animate.move_to(...)` natively. Lets the agent focus on the "aha" cell with a satisfying push-in, then pull back to context. Single biggest visual upgrade after few-shot prompts. Touches `tool_executor.py` + `schemas/tools.py`. Effort: 1 day.

### <a id="aq8"></a>8. Synced TTS narration baked into video
The narration feature currently fires in the browser AFTER the user clicks Narrate. Instead, generate per-scene TTS audio (browser Whisper TTS, OpenAI TTS, or ElevenLabs) when building the lesson, sync to scene duration, and mux into the MP4 via ffmpeg. The shared output is one self-contained video that explains itself. Bigger lift but transforms Lumen from "silent animation" to "voiced lesson." Effort: 2 days.

### <a id="aq9"></a>9. Variable pacing + insight emphasis
Currently every tool call is roughly the same duration. Add `pace` arg to high-impact tools: `emphasize(element_id, pace="slow")` runs at half-speed with a longer pause. Add explicit `slow_down(factor)` / `speed_up(factor)` controls. Forces the agent to think about rhythm. Effort: 4 hours.

### <a id="aq10"></a>10. Adaptive lesson length + complexity
Today every lesson is 2–4 scenes at fixed visual density. Add an optional `target_minutes` param to the agent: 60s for a quick intuition, 180s for a deeper walk-through, 300s for a full tutorial. Agent adjusts scene count and per-scene tool-call count accordingly. Effort: half day in prompts.

### <a id="aq11"></a>11. Streaming narrative plan to UI
The narrative-plan LLM call takes 3–6 seconds. Stream the response token-by-token via Server-Sent Events so the user sees "Planning a lesson about… two pointers… first we'll show the brute force…" while it's being generated. Massively reduces perceived wait time. Effort: 1 day (SSE pipeline + frontend reader).

### <a id="aq12"></a>12. Narrative style presets
Let the user pick "intuition first," "rigor first," "Socratic," or "speedrun" before generating a lesson. Each just swaps a prompt prefix. Same agent, very different feel. Lets the same problem produce wildly different lessons for different learners. Effort: 2 hours.

---

## Production readiness

### <a id="pr1"></a>13. Persistent job state in Postgres
The `_jobs` dict in `worker.py` is in-memory — restart wipes everything in-flight. Move job state to Postgres (or SQLite for hackathon-scale). Schema: `jobs(id, status, stage, progress, url, error, created_at, payload_json)`. Allows multi-worker setups and survives deploys. Effort: 1 day with SQLAlchemy.

### <a id="pr2"></a>14. Redis + RQ job queue with separate workers
Right now Flask serves HTTP AND runs Manim subprocesses on the same process. One long render blocks new requests. Move to RQ (Redis Queue) or Celery: web process enqueues, worker processes consume. Lets you scale renders independently. Required for any multi-user deploy. Effort: 1.5 days.

### <a id="pr3"></a>15. Object storage (S3 / R2) for videos
Local `media/` directory doesn't scale and is lost on container redeploy. Push rendered MP4s to S3 (or Cloudflare R2 for cheap egress), serve via signed URLs. The pinning logic in `worker.py` becomes "don't delete from S3" rather than "don't evict from local disk." Effort: 1 day.

### <a id="pr4"></a>16. Production WSGI + Docker Compose
Flask dev server is single-threaded and warns "do not use in production" on every request. Switch to gunicorn (4+ workers) or uvicorn. Wrap everything in Docker Compose: web, worker, postgres, redis. Means one `docker-compose up` brings the whole stack up locally and identically in prod. Effort: 1 day including writing Dockerfiles.

### <a id="pr5"></a>17. User accounts and auth
Currently no concept of users — shares.json is global, library is per-browser. Add auth via Supabase, Clerk, or Auth0 (cheapest dev experience). Users get their own library, share history, quiz history. Required before opening to public. Effort: 1–2 days.

### <a id="pr6"></a>18. Rate limiting and quotas
Anyone can hit `/api/direct-lesson` 1000 times right now. Add `flask-limiter`: anonymous users get 10 renders/day per IP, logged-in users 50/day on free tier. Critical because each render is ~$0.05–0.10 of LLM + compute. Effort: 3 hours.

### <a id="pr7"></a>19. CI/CD via GitHub Actions
No CI currently — tests only run when you run them locally. Add `.github/workflows/test.yml`: on PR, run `pytest backend/tests/ -m "not integration"` + `cd frontend && tsc --noEmit && npm run build`. Block merge if anything fails. Add a deploy workflow (Fly.io, Railway, Render — all support Python+Docker cheaply). Effort: 4 hours.

### <a id="pr8"></a>20. Sentry error tracking (front + back)
Today errors silently fail or just log to console. Wire Sentry SDK in both Flask and React. Free tier covers 5k events/month — plenty for early users. Tags: domain (math/dsa), scene type, stage. Lets you actually diagnose what breaks for real users. Effort: 2 hours.

### <a id="pr9"></a>21. OpenAPI schema → typed frontend client
Frontend types like `ParsedProblem` are hand-maintained and drift from the backend's Pydantic models. Use `flask-openapi3` or `apispec` to auto-generate an OpenAPI schema from the Pydantic models, then run `openapi-typescript` in the frontend build to generate `api.gen.ts`. Single source of truth, no drift. Effort: 1 day.

### <a id="pr10"></a>22. Secrets management + env separation
`backend/.env` works locally but isn't suitable for prod. Use a real secrets manager: GitHub Actions Secrets for CI, Doppler / Infisical / SOPS for runtime. Separate dev / staging / prod env configs. Document which keys are required vs optional. Effort: half day.

### <a id="pr11"></a>23. CDN in front of /media/ + cache headers
Videos are served straight from Flask with no `Cache-Control`, no compression, no CDN. Put Cloudflare in front of the static media path, set `Cache-Control: public, max-age=31536000, immutable` (videos never change), and serve them edge-cached. Drastically reduces backend load. Effort: 2 hours config.

### <a id="pr12"></a>24. Performance + bundle-size budgets in CI
The frontend has crept from 130 kB → 666 kB → back down to 345 kB. Add a CI check that fails if the main chunk grows over 400 kB. Same for Lighthouse score on the home page (must stay ≥90). Prevents silent regression. Effort: 3 hours.

---

## New features

### <a id="nf1"></a>25. PWA install + offline shell
The library page already plays videos offline (IndexedDB). Take it further: ship a service worker that caches the app shell, manifest.json with icons, "Add to Home Screen" support. Lumen becomes installable on phones and laptops as a real app. Effort: half day (Vite has a `vite-plugin-pwa` for this).

### <a id="nf2"></a>26. Multi-language code editor (JS, C++)
Pyodide handles Python in-browser. Add Wasm-Java (or just JS native) and `wasm-clang` for C++. Switch language with a dropdown above Monaco — tool sees three execution backends. Critical for LeetCode users who think in C++/Java. Bigger lift: 2 days mostly for getting the toolchains stable.

### <a id="nf3"></a>27. Compare user solution to optimal in-browser
After the user writes their solution in the editor and hits Run, automatically also run the agent's pseudocode on the same inputs and show a diff: their result vs expected, their runtime vs expected. Turns the editor from a scratchpad into a real practice tool. Effort: 1 day.

### <a id="nf4"></a>28. Spaced repetition for saved videos
Saved-Library items get an SRS score. After 1 day, 3 days, 7 days — the app prompts "Remember this? Take the quiz again." Wire to existing `/api/quiz` endpoint. The library becomes a study tool, not just storage. Effort: 1 day backend + UI.

### <a id="nf5"></a>29. Lesson playlists / courses
Group saved lessons into ordered playlists. "DP for beginners" = 8 saved lessons in a recommended order. Export a playlist as a single concatenated MP4. Users can share playlists by URL. Effort: 1.5 days.

### <a id="nf6"></a>30. Real-time collaborative notes
Two users open the same note → see each other's cursors → highlight a phrase → both see the analysis panel slide in. Y.js + WebSocket. Big lift but unlocks classroom use. Effort: 3 days (Y.js is the heavy part).

### <a id="nf7"></a>31. Public lesson library + discovery
Today shares are private (need the short code). Add an opt-in "publish to public" toggle. Public page shows trending lessons, recent additions, filter by topic. Social proof + discovery drives adoption. Effort: 2 days.

### <a id="nf8"></a>32. Embed widget (single-lesson iframe)
`<iframe src="https://lumen.app/embed/<shareCode>" />`. Teachers can embed a Lumen lesson on their class blog. Strip the chrome, autoplay the video, show only the analysis panel. Effort: half day.

### <a id="nf9"></a>33. Voice input via browser Whisper
Click a mic button, speak the problem, Whisper transcribes locally, send to the analyzer. Mobile-first input method. Use `transformers.js` Whisper tiny model (~75 MB, runs in browser). Effort: 1 day.

### <a id="nf10"></a>34. Adaptive difficulty driven by quiz history
After every render, the quiz feature records performance. Over time, the lesson director knows "user got Kadane's wrong twice, so the next time they encounter it, spend longer on the invariant." Closed feedback loop. Effort: 2 days.

### <a id="nf11"></a>35. Topic prerequisite graph
A visual map: "to understand union-find, learn arrays and trees first." Each node is a scene type, edges are prerequisites. Click a node → see the lesson. Users navigate by curiosity. Effort: 1.5 days (graph data is small but layout takes care).

### <a id="nf12"></a>36. Export lessons as PDF or MP4 download
"Save to Library" stores in IndexedDB; "Export PDF" generates a printable handout (title, scene thumbnails, captions, code, explanation) via `react-pdf`. "Download MP4" gives the actual rendered video file. Effort: 1 day (PDF is the heavier piece).

---

## Recommended priorities

If you have a weekend → **#1 + #2 + #7** transforms lesson quality immediately.

If you want to ship publicly → **#13 + #14 + #16 + #17 + #18 + #19** is the minimum production stack.

If you want viral growth → **#25 + #31 + #32 + #25 + #33** unlocks discovery and mobile use.

If you want to differentiate → **#2 + #8 + #30** are the moats: stateful narratives, voiced lessons, real-time collab.
