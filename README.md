# Annie

Editorial note-taking web app with Manim-style animations. Highlight a concept in your notes and watch it animate.

## Quick start

```bash
npm install
npm run dev
```

Open http://localhost:5173.

## Stack

- React 18 + TypeScript
- Vite
- Tailwind CSS
- framer-motion (animations)
- lucide-react (icons)
- Cormorant Garamond + Inter (fonts, loaded from Google Fonts in `index.html`)

## What works out of the box

Everything renders and is interactive. All backend calls are mocked so you can demo the full UX without a server. Notes persist to `localStorage`.

- **Home** — placeholder page (per the brief)
- **Notes** — rich-text editor with bold, italic, highlight, side notes, and "highlight to animate"
- **Animations** — gallery of supported topics (calc, arithmetic, DSA, physics, linalg)
- **Import notes** — upload a PDF/photo → mock OCR → mock Gemini Flash structures it into a titled note
- **Import problem** — upload a textbook problem → mock OCR → mock Gemini Flash identifies the topic → animation + breakdown

## What's mocked (and where to swap in real calls)

All mocks live at the top of `src/App.tsx`, prefixed `MOCK_`:

| Mock function | Replace with |
|---|---|
| `MOCK_fetchTopics` | `GET ${VITE_FLASK_URL}/api/topics` |
| `MOCK_generateAnimation` | `POST ${VITE_FLASK_URL}/api/animate` |
| `MOCK_ocrFile` | `POST ${VITE_BACKEND_URL}/api/ocr` (multipart) |
| `MOCK_formatNoteFromText` | `POST ${VITE_BACKEND_URL}/api/format-note` |
| `MOCK_parseProblem` | `POST ${VITE_BACKEND_URL}/api/parse-problem` |
| `MOCK_explainProblem` | `POST ${VITE_BACKEND_URL}/api/breakdown` |

## Gemini model policy

| Tier | Model | Use case |
|---|---|---|
| Primary | `gemini-3-flash` | All Flash calls (OCR, formatting, problem parsing, breakdown) |
| Fallback | `gemini-2.5-flash` | Retry on 429 / quota errors |
| **Do not use** | `gemini-2.0-flash` | **Shutting down June 1, 2026** |

The fallback chain belongs in your Express backend, not the frontend. The frontend just hits `/api/<endpoint>` and trusts the response.

## Security note

`VITE_*` env vars are **inlined into the production bundle** and visible to every user. Never put `GEMINI_API_KEY` (or any secret) in `.env` with a `VITE_` prefix. Secrets go in your Express backend's `.env` (no prefix), server-side only.

## Project structure

```
annie-app/
├── index.html              Google Fonts + root mount
├── src/
│   ├── main.tsx            React entry
│   ├── App.tsx             Everything: routes, components, mocks
│   └── index.css           Tailwind directives + resets
├── public/
│   └── favicon.svg         Sparkle mark
├── .env.example            Env var template (copy to .env)
├── .gitignore              Excludes .env explicitly
└── package.json
```

## Backend contracts

Build these endpoints in your Express + Flask services. Frontend types are in `src/App.tsx`.

```
GET  ${VITE_FLASK_URL}/api/topics
     -> { topics: AnimatableTopic[] }

POST ${VITE_FLASK_URL}/api/animate
     body: { topic: AnimatableTopic, params?: object }
     -> { videoUrl: string, status: "ready" | "generating" }

POST ${VITE_BACKEND_URL}/api/ocr
     body: multipart file
     -> { text: string }
     server: Gemini 3 Flash vision → fallback Gemini 2.5 Flash

POST ${VITE_BACKEND_URL}/api/format-note
     body: { rawText: string }
     -> { title: string, html: string }
     server: Gemini 3 Flash → fallback Gemini 2.5 Flash

POST ${VITE_BACKEND_URL}/api/parse-problem
     body: { rawText: string, topics: AnimatableTopic[] }
     -> { problem: string, topicId: string | null }
     server: Gemini 3 Flash → fallback Gemini 2.5 Flash

POST ${VITE_BACKEND_URL}/api/breakdown
     body: { problem: string, topic: AnimatableTopic }
     -> { sections: { label: string, body: string }[] }
     server: Gemini 3 Flash → fallback Gemini 2.5 Flash
```

## Build for production

```bash
npm run build
npm run preview
```
