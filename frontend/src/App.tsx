// Annie — Editorial note-taking app with Manim-style animations
// Single-file React 18 + TypeScript artifact.
//
// PORTING TO VITE:
// 1. Drop this file into src/App.tsx
// 2. Install: framer-motion lucide-react
// 3. Add Tailwind (or replace className strings — Tailwind classes are used throughout)
// 4. Add Google Fonts <link> for Cormorant Garamond + Inter + JetBrains Mono in index.html
// 5. Replace the MOCK_* functions with real backend calls
//
// GEMINI MODEL POLICY (current as of May 2026 — verify before shipping):
//   PRIMARY: gemini-3-flash         (latest stable Flash, released Apr 2026)
//   FALLBACK: gemini-2.5-flash      (older but stable; use on rate-limit/quota errors)
//   DO NOT USE: gemini-2.0-flash    (shuts down June 1, 2026)
// The fallback chain lives in your BACKEND, not the frontend. The Express proxy is
// responsible for catching 429/quota errors from the primary model and retrying on
// the fallback. The frontend just calls /api/<endpoint> and trusts the result.
//
// ENV VARS (Vite-style, frontend):
//   VITE_FLASK_URL    — your Flask + Manim service base URL
//   VITE_BACKEND_URL  — your Express proxy that calls Gemini (Flash 3 + Flash 2.5 fallback)
//
// ENV VARS (backend only — NEVER prefix with VITE_):
//   GEMINI_API_KEY    — server-side only. Vite inlines VITE_* vars into the bundle,
//                       so anything prefixed VITE_ ships to every user's browser.
//
// BACKEND ENDPOINTS expected:
//   GET  VITE_FLASK_URL/api/topics              -> { topics: AnimatableTopic[] }
//   POST VITE_FLASK_URL/api/animate             { topic, params } -> { videoUrl, status }
//   POST VITE_BACKEND_URL/api/ocr               multipart file -> { text }
//   POST VITE_BACKEND_URL/api/format-note       { rawText } -> { title, html }      (Gemini Flash formats OCR'd text into note structure)
//   POST VITE_BACKEND_URL/api/parse-problem     { rawText } -> { problem, topicId } (Gemini Flash identifies which animatable topic the problem is)
//   POST VITE_BACKEND_URL/api/breakdown         { problem, topic } -> { sections } 

import React, { useState, useEffect, useRef, useMemo, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Home,
  FileText,
  Play,
  Upload,
  Search,
  Plus,
  Star,
  Sparkles,
  Bold,
  Italic,
  Highlighter,
  StickyNote,
  Trash2,
  X,
  Check,
  Loader2,
  FileImage,
  ChevronRight,
  Tag,
} from "lucide-react";

// ─────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────

type Route = "home" | "notes" | "animations" | "import-notes" | "import-animations";

interface SideNote {
  id: string;
  anchor: string; // text the side note is anchored to
  body: string;
  createdAt: number;
}

interface Note {
  id: string;
  title: string;
  contentHtml: string; // contenteditable HTML
  sideNotes: SideNote[];
  tags: string[];
  updatedAt: number;
  createdAt: number;
}

interface AnimatableTopic {
  id: string;
  name: string;
  category: "calculus" | "arithmetic" | "dsa" | "physics" | "linalg";
  keywords: string[];
  description: string;
}

interface BreakdownSection {
  label: string;
  body: string;
}

// ─────────────────────────────────────────────────────────────
// Mock backend — REPLACE WITH REAL CALLS
// ─────────────────────────────────────────────────────────────

const MOCK_TOPICS: AnimatableTopic[] = [
  {
    id: "merge-sort",
    name: "Merge Sort",
    category: "dsa",
    keywords: ["merge sort", "mergesort", "divide and conquer sort"],
    description: "Recursive divide-and-merge visualization with comparison highlights.",
  },
  {
    id: "quick-sort",
    name: "Quick Sort",
    category: "dsa",
    keywords: ["quick sort", "quicksort", "partition"],
    description: "Pivot-based partitioning shown step by step.",
  },
  {
    id: "binary-search",
    name: "Binary Search",
    category: "dsa",
    keywords: ["binary search", "log n search"],
    description: "Halving the search space on a sorted array.",
  },
  {
    id: "chain-rule",
    name: "Chain Rule",
    category: "calculus",
    keywords: ["chain rule", "composite derivative", "f(g(x))"],
    description: "Derivative of nested functions, layer by layer.",
  },
  {
    id: "washer-method",
    name: "Washer Method",
    category: "calculus",
    keywords: ["washer method", "volume of revolution", "disk method"],
    description: "Volume of solids of revolution using stacked washers.",
  },
  {
    id: "shell-method",
    name: "Cylindrical Shell Method",
    category: "calculus",
    keywords: ["cylindrical shell", "shell method", "shells"],
    description: "Volume by unwrapping concentric cylindrical shells.",
  },
  {
    id: "long-division",
    name: "Long Division",
    category: "arithmetic",
    keywords: ["long division", "divide"],
    description: "Step-by-step division algorithm.",
  },
  {
    id: "derivative-power-rule",
    name: "Power Rule",
    category: "calculus",
    keywords: ["power rule", "derivative of x^n"],
    description: "Why d/dx[x^n] = n·x^(n-1).",
  },
  {
    id: "torque",
    name: "Torque",
    category: "physics",
    keywords: ["torque", "rotational force"],
    description: "Force × lever arm visualized on a rotating body.",
  },
  {
    id: "matrix-multiply",
    name: "Matrix Multiplication",
    category: "linalg",
    keywords: ["matrix multiply", "matmul"],
    description: "Row-by-column dot products animated.",
  },
];

async function fetchTopics(): Promise<AnimatableTopic[]> {
  const flaskUrl =
    (import.meta.env.VITE_FLASK_URL as string | undefined) ||
    "http://localhost:5000";
  try {
    const res = await fetch(`${flaskUrl}/topics`);
    if (!res.ok) throw new Error(`/topics ${res.status}`);
    const data = await res.json();
    return Array.isArray(data.topics) ? data.topics : MOCK_TOPICS;
  } catch {
    return MOCK_TOPICS;
  }
}

async function generateAnimation(
  topic: AnimatableTopic,
  extraContext?: string
): Promise<{ videoUrl: string; status: "ready" | "error"; error?: string }> {
  const flaskUrl =
    (import.meta.env.VITE_FLASK_URL as string | undefined) ||
    "http://localhost:5000";
  const question = extraContext
    ? `${topic.name}: ${extraContext}`
    : `${topic.name}: ${topic.description}`;

  try {
    const askRes = await fetch(`${flaskUrl}/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    if (!askRes.ok) {
      const detail = await askRes.text().catch(() => "");
      return { videoUrl: `placeholder://${topic.id}`, status: "error",
                error: `/ask ${askRes.status}: ${detail.slice(0, 120)}` };
    }
    const ask = await askRes.json();
    const jobId: string = ask.job_id;
    if (!jobId) {
      return { videoUrl: `placeholder://${topic.id}`, status: "error",
                error: "/ask returned no job_id" };
    }

    const deadline = Date.now() + 120_000;   // 2-minute timeout
    while (Date.now() < deadline) {
      await new Promise((r) => setTimeout(r, 800));
      const statusRes = await fetch(`${flaskUrl}/status/${jobId}`);
      if (!statusRes.ok) continue;
      const job = await statusRes.json();
      if (job.status === "done" && job.url) {
        return { videoUrl: `${flaskUrl}${job.url}`, status: "ready" };
      }
      if (job.status === "error") {
        return { videoUrl: `placeholder://${topic.id}`, status: "error",
                  error: job.error || "render failed" };
      }
    }
    return { videoUrl: `placeholder://${topic.id}`, status: "error",
              error: "render timed out after 120s" };
  } catch (e) {
    return { videoUrl: `placeholder://${topic.id}`, status: "error",
              error: e instanceof Error ? e.message : String(e) };
  }
}

// MOCK: replace with `await fetch(\`${import.meta.env.VITE_BACKEND_URL}/api/ocr\`, { method: 'POST', body: formData })`
// Backend should:
//   1. Accept multipart file
//   2. Call Gemini 3 Flash with the image/PDF (Gemini supports vision natively, no separate OCR needed)
//   3. On 429/quota error → retry with Gemini 2.5 Flash
//   4. Return raw extracted text
// DO NOT call Gemini directly from the frontend — VITE_* env vars ship to the browser.
async function MOCK_ocrFile(file: File): Promise<{ text: string }> {
  await new Promise((r) => setTimeout(r, 1500));
  return {
    text: `[Mock OCR output from ${file.name}]\n\nFind the volume of the solid generated by revolving the region bounded by y = x², y = 0, and x = 2 about the y-axis.\n\n(Replace this with a real Gemini Flash vision call from your Express backend.)`,
  };
}

// MOCK: replace with `POST ${VITE_BACKEND_URL}/api/format-note { rawText }`
// Backend prompts Gemini Flash to take messy OCR text and structure it as a proper note:
//   - Extract a title
//   - Add headings, paragraphs, lists where appropriate
//   - Return clean HTML the editor can render
// Falls back from gemini-3-flash → gemini-2.5-flash on quota errors.
async function MOCK_formatNoteFromText(rawText: string): Promise<{ title: string; html: string }> {
  await new Promise((r) => setTimeout(r, 1400));
  // Cheap heuristic for the mock — real Gemini call would be far better
  const lines = rawText.split("\n").filter((l) => l.trim());
  const title = lines[0]?.slice(0, 60) || "Imported note";
  const body = lines
    .slice(1)
    .map((l) => `<p>${l}</p>`)
    .join("");
  return {
    title: title.replace(/^\[.*?\]\s*/, "").trim() || "Imported note",
    html:
      `<h2>Summary</h2><p>${rawText.split("\n\n")[0]?.slice(0, 200) || ""}</p>` +
      `<h2>Full content</h2>${body}`,
  };
}

// MOCK: replace with `POST ${VITE_BACKEND_URL}/api/parse-problem { rawText }`
// Backend prompts Gemini Flash with the OCR'd problem + the list of available animation topics,
// and asks it to identify which topic best matches. Returns the cleaned problem statement and topic id.
// Falls back from gemini-3-flash → gemini-2.5-flash on quota errors.
async function MOCK_parseProblem(
  rawText: string,
  topics: AnimatableTopic[]
): Promise<{ problem: string; topicId: string | null }> {
  await new Promise((r) => setTimeout(r, 1200));
  // Mock: find topic by keyword match (real backend uses Gemini reasoning)
  const matched = findMatchingTopic(rawText, topics);
  return {
    problem: rawText.replace(/^\[.*?\]\s*/, "").trim(),
    topicId: matched?.id || null,
  };
}

async function explainProblem(
  problem: string,
  topic: AnimatableTopic
): Promise<BreakdownSection[]> {
  const flaskUrl =
    (import.meta.env.VITE_FLASK_URL as string | undefined) ||
    "http://localhost:5000";
  try {
    const res = await fetch(`${flaskUrl}/breakdown`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        problem,
        topicId: topic.id,
        topicName: topic.name,
        topicDescription: topic.description,
      }),
    });
    if (!res.ok) throw new Error(`/breakdown ${res.status}`);
    const data = await res.json();
    if (Array.isArray(data.sections) && data.sections.length > 0) {
      return data.sections;
    }
  } catch {
    // fall through to local fallback
  }
  return [
    { label: "Method", body: `${topic.name} — see animation for the visual intuition.` },
    { label: "Key idea", body: topic.description },
  ];
}

// ─────────────────────────────────────────────────────────────
// localStorage persistence
// ─────────────────────────────────────────────────────────────

const STORAGE_KEY = "annie_notes_v1";

function loadNotes(): Note[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    return JSON.parse(raw);
  } catch {
    return [];
  }
}

function saveNotes(notes: Note[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(notes));
  } catch {
    // ignore
  }
}

function uid() {
  return Math.random().toString(36).slice(2, 10);
}

// ─────────────────────────────────────────────────────────────
// Topic detection — match highlighted text against animatable topics
// ─────────────────────────────────────────────────────────────

function findMatchingTopic(text: string, topics: AnimatableTopic[]): AnimatableTopic | null {
  const t = text.toLowerCase().trim();
  if (!t) return null;
  for (const topic of topics) {
    for (const kw of topic.keywords) {
      if (t.includes(kw.toLowerCase())) return topic;
    }
  }
  return null;
}

// ─────────────────────────────────────────────────────────────
// Decorative botanical SVG
// ─────────────────────────────────────────────────────────────

const BotanicalAccent: React.FC<{ className?: string; style?: React.CSSProperties }> = ({ className, style }) => (
  <svg viewBox="0 0 120 120" className={className} style={style} fill="none" stroke="currentColor" strokeWidth="0.8">
    <path d="M60 110 Q60 60 60 10" strokeLinecap="round" />
    <path d="M60 90 Q40 80 30 60" strokeLinecap="round" />
    <path d="M60 80 Q80 70 90 50" strokeLinecap="round" />
    <path d="M60 65 Q42 58 35 40" strokeLinecap="round" />
    <path d="M60 55 Q78 48 85 32" strokeLinecap="round" />
    <ellipse cx="30" cy="60" rx="6" ry="3" transform="rotate(-30 30 60)" />
    <ellipse cx="90" cy="50" rx="6" ry="3" transform="rotate(30 90 50)" />
    <ellipse cx="35" cy="40" rx="5" ry="2.5" transform="rotate(-30 35 40)" />
    <ellipse cx="85" cy="32" rx="5" ry="2.5" transform="rotate(30 85 32)" />
  </svg>
);

const Sparkle: React.FC<{ className?: string; style?: React.CSSProperties }> = ({ className, style }) => (
  <svg viewBox="0 0 16 16" className={className} style={style} fill="currentColor">
    <path d="M8 0 L9 7 L16 8 L9 9 L8 16 L7 9 L0 8 L7 7 Z" />
  </svg>
);

// ─────────────────────────────────────────────────────────────
// Sidebar
// ─────────────────────────────────────────────────────────────

const Sidebar: React.FC<{
  route: Route;
  onRoute: (r: Route) => void;
  onNewNote: () => void;
}> = ({ route, onRoute, onNewNote }) => {
  const items: { key: Route; label: string; icon: React.ReactNode }[] = [
    { key: "home", label: "Home", icon: <Home size={16} strokeWidth={1.5} /> },
    { key: "notes", label: "Notes", icon: <FileText size={16} strokeWidth={1.5} /> },
    { key: "animations", label: "Animations", icon: <Play size={16} strokeWidth={1.5} /> },
    { key: "import-notes", label: "Import notes", icon: <FileImage size={16} strokeWidth={1.5} /> },
    { key: "import-animations", label: "Import problem", icon: <Upload size={16} strokeWidth={1.5} /> },
  ];

  return (
    <aside
      className="flex flex-col h-screen border-r"
      style={{
        width: 260,
        background: "#FBF7F1",
        borderColor: "#DED0C2",
      }}
    >
      <div className="px-6 pt-8 pb-6 flex items-center gap-2">
        <Sparkle className="w-3 h-3" style={{ color: "#C8A47B" }} />
        <span
          style={{
            fontFamily: "'Cormorant Garamond', serif",
            fontSize: 26,
            fontWeight: 600,
            color: "#2F261F",
            letterSpacing: "-0.01em",
          }}
        >
          Annie
        </span>
      </div>

      <button
        onClick={onNewNote}
        className="mx-4 mb-6 px-4 py-2.5 rounded-full flex items-center gap-2 transition-all"
        style={{
          background: "#705642",
          color: "#FFFFFF",
          fontFamily: "Inter, sans-serif",
          fontSize: 14,
          fontWeight: 500,
        }}
        onMouseEnter={(e) => (e.currentTarget.style.background = "#5B4434")}
        onMouseLeave={(e) => (e.currentTarget.style.background = "#705642")}
      >
        <Plus size={15} strokeWidth={1.8} />
        New note
      </button>

      <nav className="px-2 flex-1">
        {items.map((it) => {
          const active = route === it.key;
          return (
            <button
              key={it.key}
              onClick={() => onRoute(it.key)}
              className="w-full px-4 py-2.5 mb-1 rounded-full flex items-center gap-3 text-left transition-colors"
              style={{
                background: active ? "#E9D7BE" : "transparent",
                color: active ? "#5B4434" : "#5E4C40",
                fontFamily: "Inter, sans-serif",
                fontSize: 14,
                fontWeight: active ? 500 : 400,
              }}
              onMouseEnter={(e) => {
                if (!active) e.currentTarget.style.background = "#F0E4D3";
              }}
              onMouseLeave={(e) => {
                if (!active) e.currentTarget.style.background = "transparent";
              }}
            >
              {it.icon}
              {it.label}
            </button>
          );
        })}
      </nav>

      <div className="p-6 relative" style={{ color: "#C8A47B" }}>
        <BotanicalAccent className="w-16 h-16 opacity-40 absolute bottom-2 right-2" />
        <p
          style={{
            fontFamily: "'Cormorant Garamond', serif",
            fontStyle: "italic",
            fontSize: 13,
            color: "#9A8677",
            lineHeight: 1.5,
          }}
        >
          A softer way to learn.
        </p>
      </div>
    </aside>
  );
};

// ─────────────────────────────────────────────────────────────
// Home page (placeholder)
// ─────────────────────────────────────────────────────────────

const HomePage: React.FC = () => (
  <div className="h-full overflow-auto" style={{ background: "#F5F0EA" }}>
    <div className="max-w-4xl mx-auto px-12 py-20 relative">
      <BotanicalAccent
        className="w-32 h-32 absolute top-12 right-12 opacity-30"
        style={{ color: "#C8A47B" } as React.CSSProperties}
      />
      <div className="flex items-center gap-2 mb-6">
        <Sparkle className="w-3 h-3" style={{ color: "#C8A47B" }} />
        <span
          style={{
            fontFamily: "'Cormorant Garamond', serif",
            fontStyle: "italic",
            fontSize: 14,
            color: "#9A8677",
            letterSpacing: "0.05em",
          }}
        >
          A softer way to study
        </span>
      </div>
      <h1
        style={{
          fontFamily: "'Cormorant Garamond', serif",
          fontSize: 84,
          fontWeight: 600,
          color: "#2F261F",
          lineHeight: 0.95,
          letterSpacing: "-0.02em",
          marginBottom: 24,
        }}
      >
        Notes that
        <br />
        <em style={{ color: "#705642" }}>see for you.</em>
      </h1>
      <p
        style={{
          fontFamily: "Inter, sans-serif",
          fontSize: 18,
          color: "#5E4C40",
          lineHeight: 1.6,
          maxWidth: 540,
          marginBottom: 48,
        }}
      >
        Highlight a concept and watch it animate. Capture lectures, import problems,
        organize ideas — all in one calm, editorial workspace.
      </p>

      <div
        className="rounded-3xl p-12 text-center relative overflow-hidden"
        style={{
          background: "#FFF9F0",
          border: "1px solid #DED0C2",
          boxShadow: "0 8px 24px rgba(70, 49, 34, 0.08)",
        }}
      >
        <Sparkles
          className="absolute top-4 right-4 w-5 h-5 opacity-40"
          style={{ color: "#C8A47B" }}
          strokeWidth={1.2}
        />
        <p
          style={{
            fontFamily: "'Cormorant Garamond', serif",
            fontStyle: "italic",
            fontSize: 28,
            color: "#705642",
            marginBottom: 12,
          }}
        >
          Research findings coming soon
        </p>
        <p
          style={{
            fontFamily: "Inter, sans-serif",
            fontSize: 14,
            color: "#9A8677",
          }}
        >
          This page will host the cognitive-science evidence behind why visual learning works for every student.
        </p>
      </div>
    </div>
  </div>
);

// ─────────────────────────────────────────────────────────────
// Notes page
// ─────────────────────────────────────────────────────────────

const NotesPage: React.FC<{
  notes: Note[];
  topics: AnimatableTopic[];
  onUpdate: (note: Note) => void;
  onDelete: (id: string) => void;
  onNew: () => void;
  selectedId: string | null;
  setSelectedId: (id: string | null) => void;
}> = ({ notes, topics, onUpdate, onDelete, onNew, selectedId, setSelectedId }) => {
  const selected = notes.find((n) => n.id === selectedId) || null;
  const [search, setSearch] = useState("");

  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    return notes
      .filter(
        (n) =>
          !q ||
          n.title.toLowerCase().includes(q) ||
          n.contentHtml.toLowerCase().includes(q)
      )
      .sort((a, b) => b.updatedAt - a.updatedAt);
  }, [notes, search]);

  return (
    <div className="flex h-full" style={{ background: "#F5F0EA" }}>
      {/* Notes list */}
      <div
        className="flex flex-col"
        style={{ width: 340, borderRight: "1px solid #DED0C2", background: "#F5F0EA" }}
      >
        <div className="px-6 pt-8 pb-4">
          <h2
            style={{
              fontFamily: "'Cormorant Garamond', serif",
              fontSize: 32,
              fontWeight: 600,
              color: "#2F261F",
              marginBottom: 16,
            }}
          >
            All notes
          </h2>
          <div className="relative">
            <Search
              size={14}
              strokeWidth={1.5}
              className="absolute left-4 top-1/2 -translate-y-1/2"
              style={{ color: "#9A8677" }}
            />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search notes..."
              className="w-full pl-10 pr-4 py-2.5 rounded-full outline-none transition-colors"
              style={{
                background: "#FFF9F0",
                border: "1px solid #D8C7B5",
                fontFamily: "Inter, sans-serif",
                fontSize: 14,
                color: "#3E2E25",
              }}
              onFocus={(e) => (e.currentTarget.style.borderColor = "#C8A47B")}
              onBlur={(e) => (e.currentTarget.style.borderColor = "#D8C7B5")}
            />
          </div>
        </div>

        <div className="flex-1 overflow-auto px-4 pb-6">
          {filtered.length === 0 && (
            <div className="px-2 py-8 text-center">
              <p
                style={{
                  fontFamily: "'Cormorant Garamond', serif",
                  fontStyle: "italic",
                  fontSize: 18,
                  color: "#9A8677",
                  marginBottom: 8,
                }}
              >
                Your first thought belongs here.
              </p>
              <button
                onClick={onNew}
                className="mt-4 px-4 py-2 rounded-full"
                style={{
                  background: "#705642",
                  color: "#FFFFFF",
                  fontFamily: "Inter, sans-serif",
                  fontSize: 13,
                }}
              >
                Create note
              </button>
            </div>
          )}
          {filtered.map((n) => {
            const active = n.id === selectedId;
            const preview = n.contentHtml.replace(/<[^>]+>/g, " ").slice(0, 90);
            return (
              <button
                key={n.id}
                onClick={() => setSelectedId(n.id)}
                className="w-full text-left p-4 mb-2 rounded-2xl transition-all"
                style={{
                  background: active ? "#FFF9F0" : "#FFFFFF",
                  border: `1px solid ${active ? "#C8A47B" : "#DED0C2"}`,
                  boxShadow: active ? "0 8px 24px rgba(70, 49, 34, 0.08)" : "none",
                }}
              >
                <div
                  style={{
                    fontFamily: "'Cormorant Garamond', serif",
                    fontSize: 18,
                    fontWeight: 600,
                    color: "#2F261F",
                    marginBottom: 4,
                  }}
                >
                  {n.title || "Untitled thought"}
                </div>
                <div
                  style={{
                    fontFamily: "Inter, sans-serif",
                    fontSize: 13,
                    color: "#9A8677",
                    lineHeight: 1.5,
                    marginBottom: 6,
                    overflow: "hidden",
                    display: "-webkit-box",
                    WebkitLineClamp: 2,
                    WebkitBoxOrient: "vertical",
                  }}
                >
                  {preview || "Empty"}
                </div>
                <div
                  style={{
                    fontFamily: "Inter, sans-serif",
                    fontSize: 11,
                    color: "#9A8677",
                  }}
                >
                  {new Date(n.updatedAt).toLocaleDateString("en-US", {
                    month: "short",
                    day: "numeric",
                  })}
                  {n.sideNotes.length > 0 && (
                    <span className="ml-2">· {n.sideNotes.length} side note{n.sideNotes.length === 1 ? "" : "s"}</span>
                  )}
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Editor */}
      <div className="flex-1 overflow-auto">
        {selected ? (
          <NoteEditor
            key={selected.id}
            note={selected}
            topics={topics}
            onUpdate={onUpdate}
            onDelete={() => {
              onDelete(selected.id);
              setSelectedId(null);
            }}
          />
        ) : (
          <div className="h-full flex items-center justify-center px-12">
            <div className="text-center max-w-md">
              <BotanicalAccent
                className="w-24 h-24 mx-auto mb-6 opacity-40"
                style={{ color: "#C8A47B" } as React.CSSProperties}
              />
              <p
                style={{
                  fontFamily: "'Cormorant Garamond', serif",
                  fontStyle: "italic",
                  fontSize: 26,
                  color: "#705642",
                  marginBottom: 12,
                }}
              >
                Select a note, or begin a new one.
              </p>
              <p
                style={{
                  fontFamily: "Inter, sans-serif",
                  fontSize: 14,
                  color: "#9A8677",
                }}
              >
                Highlight any concept while you write to bring it to life.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

// ─────────────────────────────────────────────────────────────
// Note editor — contenteditable + selection toolbar + side notes
// ─────────────────────────────────────────────────────────────

const NoteEditor: React.FC<{
  note: Note;
  topics: AnimatableTopic[];
  onUpdate: (note: Note) => void;
  onDelete: () => void;
}> = ({ note, topics, onUpdate, onDelete }) => {
  const editorRef = useRef<HTMLDivElement>(null);
  const [title, setTitle] = useState(note.title);
  const [toolbar, setToolbar] = useState<{
    visible: boolean;
    x: number;
    y: number;
    selectedText: string;
    matchedTopic: AnimatableTopic | null;
  }>({ visible: false, x: 0, y: 0, selectedText: "", matchedTopic: null });
  const [animating, setAnimating] = useState<{
    topic: AnimatableTopic;
    breakdown: BreakdownSection[] | null;
    loading: boolean;
    videoUrl?: string;
    error?: string;
  } | null>(null);
  const [sideNoteDraft, setSideNoteDraft] = useState<{ anchor: string; body: string } | null>(null);

  // Initialize editor content once
  useEffect(() => {
    if (editorRef.current && editorRef.current.innerHTML !== note.contentHtml) {
      editorRef.current.innerHTML = note.contentHtml;
    }
    setTitle(note.title);
  }, [note.id]);

  // Selection toolbar logic
  const handleSelection = useCallback(() => {
    const sel = window.getSelection();
    if (!sel || sel.isCollapsed || !editorRef.current) {
      setToolbar((t) => ({ ...t, visible: false }));
      return;
    }
    const range = sel.getRangeAt(0);
    if (!editorRef.current.contains(range.commonAncestorContainer)) {
      setToolbar((t) => ({ ...t, visible: false }));
      return;
    }
    const text = sel.toString();
    if (!text.trim()) {
      setToolbar((t) => ({ ...t, visible: false }));
      return;
    }
    const rect = range.getBoundingClientRect();
    const editorRect = editorRef.current.getBoundingClientRect();
    const matched = findMatchingTopic(text, topics);
    setToolbar({
      visible: true,
      x: rect.left - editorRect.left + rect.width / 2,
      y: rect.top - editorRect.top - 50,
      selectedText: text,
      matchedTopic: matched,
    });
  }, [topics]);

  useEffect(() => {
    document.addEventListener("selectionchange", handleSelection);
    return () => document.removeEventListener("selectionchange", handleSelection);
  }, [handleSelection]);

  // Save content (debounced via React state lifecycle)
  const persist = useCallback(() => {
    if (!editorRef.current) return;
    onUpdate({
      ...note,
      title,
      contentHtml: editorRef.current.innerHTML,
      updatedAt: Date.now(),
    });
  }, [note, title, onUpdate]);

  useEffect(() => {
    const id = setTimeout(persist, 400);
    return () => clearTimeout(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [title]);

  const exec = (cmd: string) => {
    document.execCommand(cmd, false);
    if (editorRef.current) {
      onUpdate({
        ...note,
        title,
        contentHtml: editorRef.current.innerHTML,
        updatedAt: Date.now(),
      });
    }
  };

  const applyHighlight = () => {
    document.execCommand("hiliteColor", false, "#E9D7BE");
    if (editorRef.current) {
      onUpdate({
        ...note,
        title,
        contentHtml: editorRef.current.innerHTML,
        updatedAt: Date.now(),
      });
    }
  };

  const animate = async (topic: AnimatableTopic) => {
    setToolbar((t) => ({ ...t, visible: false }));
    setAnimating({ topic, breakdown: null, loading: true });
    const [animResult, sections] = await Promise.all([
      generateAnimation(topic, toolbar.selectedText || undefined),
      explainProblem(toolbar.selectedText, topic),
    ]);
    setAnimating({
      topic,
      breakdown: sections,
      loading: false,
      videoUrl: animResult.status === "ready" ? animResult.videoUrl : undefined,
      error:    animResult.status === "error" ? animResult.error : undefined,
    });
  };

  const startSideNote = () => {
    setSideNoteDraft({ anchor: toolbar.selectedText, body: "" });
    setToolbar((t) => ({ ...t, visible: false }));
  };

  const saveSideNote = () => {
    if (!sideNoteDraft || !sideNoteDraft.body.trim()) {
      setSideNoteDraft(null);
      return;
    }
    const newSide: SideNote = {
      id: uid(),
      anchor: sideNoteDraft.anchor,
      body: sideNoteDraft.body,
      createdAt: Date.now(),
    };
    onUpdate({
      ...note,
      sideNotes: [...note.sideNotes, newSide],
      updatedAt: Date.now(),
    });
    setSideNoteDraft(null);
  };

  const deleteSideNote = (id: string) => {
    onUpdate({
      ...note,
      sideNotes: note.sideNotes.filter((s) => s.id !== id),
      updatedAt: Date.now(),
    });
  };

  return (
    <div className="flex h-full">
      <div className="flex-1 overflow-auto" style={{ background: "#FFF9F0" }}>
        <div className="max-w-3xl mx-auto px-16 py-16 relative">
          {/* Title */}
          <div className="mb-2 flex items-center justify-between">
            <span
              style={{
                fontFamily: "Inter, sans-serif",
                fontSize: 12,
                color: "#9A8677",
                letterSpacing: "0.08em",
                textTransform: "uppercase",
              }}
            >
              {new Date(note.createdAt).toLocaleDateString("en-US", {
                month: "long",
                day: "numeric",
                year: "numeric",
              })}
            </span>
            <button
              onClick={onDelete}
              className="p-2 rounded-full transition-colors"
              style={{ color: "#9A8677" }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = "#F0E4D3";
                e.currentTarget.style.color = "#A65F50";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = "transparent";
                e.currentTarget.style.color = "#9A8677";
              }}
              title="Delete note"
            >
              <Trash2 size={16} strokeWidth={1.5} />
            </button>
          </div>

          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Untitled thought"
            className="w-full outline-none bg-transparent mb-8"
            style={{
              fontFamily: "'Cormorant Garamond', serif",
              fontSize: 48,
              fontWeight: 600,
              color: "#2F261F",
              letterSpacing: "-0.02em",
              lineHeight: 1.1,
            }}
          />

          {/* Editor */}
          <div className="relative">
            {toolbar.visible && (
              <div
                className="absolute z-20 flex items-center gap-1 px-2 py-1.5 rounded-full"
                style={{
                  left: toolbar.x,
                  top: toolbar.y,
                  transform: "translateX(-50%)",
                  background: "#FFFFFF",
                  border: "1px solid #DED0C2",
                  boxShadow: "0 18px 48px rgba(70, 49, 34, 0.16)",
                }}
              >
                <ToolbarBtn icon={<Bold size={14} strokeWidth={2} />} onClick={() => exec("bold")} label="Bold" />
                <ToolbarBtn icon={<Italic size={14} strokeWidth={2} />} onClick={() => exec("italic")} label="Italic" />
                <ToolbarBtn icon={<Highlighter size={14} strokeWidth={1.8} />} onClick={applyHighlight} label="Highlight" />
                <div style={{ width: 1, height: 16, background: "#DED0C2", margin: "0 2px" }} />
                <ToolbarBtn icon={<StickyNote size={14} strokeWidth={1.8} />} onClick={startSideNote} label="Side note" />
                {toolbar.matchedTopic && (
                  <button
                    onClick={() => animate(toolbar.matchedTopic!)}
                    className="ml-1 px-3 py-1 rounded-full flex items-center gap-1.5 transition-colors"
                    style={{
                      background: "#705642",
                      color: "#FFFFFF",
                      fontFamily: "Inter, sans-serif",
                      fontSize: 12,
                      fontWeight: 500,
                    }}
                  >
                    <Sparkles size={12} strokeWidth={2} />
                    Animate "{toolbar.matchedTopic.name}"
                  </button>
                )}
              </div>
            )}

            <div
              ref={editorRef}
              contentEditable
              suppressContentEditableWarning
              onInput={() => {
                if (editorRef.current) {
                  onUpdate({
                    ...note,
                    title,
                    contentHtml: editorRef.current.innerHTML,
                    updatedAt: Date.now(),
                  });
                }
              }}
              className="outline-none min-h-[300px]"
              style={{
                fontFamily: "Inter, sans-serif",
                fontSize: 17,
                color: "#3E2E25",
                lineHeight: 1.7,
              }}
              data-placeholder="Start writing, paste a transcript, or import something beautiful..."
            />
            <style>{`
              [contenteditable]:empty::before {
                content: attr(data-placeholder);
                color: #9A8677;
                font-style: italic;
                font-family: 'Cormorant Garamond', serif;
                font-size: 18px;
                pointer-events: none;
              }
            `}</style>
          </div>

          {/* Animation panel */}
          <AnimatePresence>
            {animating && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 20 }}
                transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
                className="mt-12 rounded-3xl overflow-hidden relative"
                style={{
                  border: "1px solid #DED0C2",
                  boxShadow: "0 12px 40px rgba(70, 49, 34, 0.10)",
                  background: "#FFFFFF",
                }}
              >
                <div className="flex items-center justify-between px-6 py-4 border-b" style={{ borderColor: "#ECE1D6" }}>
                  <div className="flex items-center gap-2">
                    <Sparkles size={14} strokeWidth={1.5} style={{ color: "#C8A47B" }} />
                    <span
                      style={{
                        fontFamily: "'Cormorant Garamond', serif",
                        fontStyle: "italic",
                        fontSize: 18,
                        color: "#705642",
                      }}
                    >
                      {animating.topic.name}
                    </span>
                  </div>
                  <button
                    onClick={() => setAnimating(null)}
                    className="p-1.5 rounded-full"
                    style={{ color: "#9A8677" }}
                  >
                    <X size={14} strokeWidth={1.5} />
                  </button>
                </div>

                {/* Animation placeholder */}
                <div
                  className="aspect-video flex items-center justify-center relative"
                  style={{ background: "#F5F0EA" }}
                >
                  {animating.loading ? (
                    <div className="flex flex-col items-center gap-3">
                      <Loader2 size={28} strokeWidth={1.2} className="animate-spin" style={{ color: "#705642" }} />
                      <p
                        style={{
                          fontFamily: "'Cormorant Garamond', serif",
                          fontStyle: "italic",
                          fontSize: 16,
                          color: "#9A8677",
                        }}
                      >
                        Rendering your animation...
                      </p>
                    </div>
                  ) : animating.videoUrl ? (
                    <video
                      src={animating.videoUrl}
                      autoPlay
                      loop
                      controls
                      className="w-full h-full object-contain"
                      style={{ background: "#0d1117" }}
                    />
                  ) : (
                    <div className="flex flex-col items-center gap-2">
                      <ManimPlaceholder topic={animating.topic} />
                      {animating.error && (
                        <p style={{ fontSize: 12, color: "#A66", fontFamily: "Inter, sans-serif" }}>
                          {animating.error}
                        </p>
                      )}
                    </div>
                  )}
                </div>

                {/* Breakdown */}
                {animating.breakdown && (
                  <div className="px-8 py-6">
                    <p
                      style={{
                        fontFamily: "Inter, sans-serif",
                        fontSize: 11,
                        color: "#9A8677",
                        letterSpacing: "0.1em",
                        textTransform: "uppercase",
                        marginBottom: 16,
                      }}
                    >
                      Problem breakdown
                    </p>
                    {animating.breakdown.map((s, i) => (
                      <div key={i} className="mb-4 flex gap-4">
                        <div
                          style={{
                            fontFamily: "'Cormorant Garamond', serif",
                            fontStyle: "italic",
                            fontSize: 16,
                            color: "#705642",
                            minWidth: 120,
                          }}
                        >
                          {s.label}
                        </div>
                        <div
                          style={{
                            fontFamily: "Inter, sans-serif",
                            fontSize: 14,
                            color: "#3E2E25",
                            lineHeight: 1.6,
                            flex: 1,
                          }}
                        >
                          {s.body}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* Side notes column */}
      {(note.sideNotes.length > 0 || sideNoteDraft) && (
        <div
          className="overflow-auto"
          style={{ width: 280, borderLeft: "1px solid #DED0C2", background: "#F5F0EA" }}
        >
          <div className="px-5 pt-8 pb-4">
            <p
              style={{
                fontFamily: "'Cormorant Garamond', serif",
                fontStyle: "italic",
                fontSize: 16,
                color: "#705642",
                marginBottom: 16,
              }}
            >
              Side notes
            </p>
          </div>
          <div className="px-4 pb-6 space-y-3">
            {note.sideNotes.map((s) => (
              <div
                key={s.id}
                className="p-4 rounded-2xl group relative"
                style={{
                  background: "#FFF9F0",
                  border: "1px solid #DED0C2",
                }}
              >
                <button
                  onClick={() => deleteSideNote(s.id)}
                  className="absolute top-2 right-2 p-1 rounded opacity-0 group-hover:opacity-100 transition-opacity"
                  style={{ color: "#9A8677" }}
                >
                  <X size={12} strokeWidth={1.5} />
                </button>
                <div
                  style={{
                    fontFamily: "Inter, sans-serif",
                    fontSize: 11,
                    color: "#9A8677",
                    fontStyle: "italic",
                    marginBottom: 6,
                    paddingLeft: 8,
                    borderLeft: "2px solid #C8A47B",
                  }}
                >
                  "{s.anchor.length > 60 ? s.anchor.slice(0, 60) + "…" : s.anchor}"
                </div>
                <div
                  style={{
                    fontFamily: "Inter, sans-serif",
                    fontSize: 13,
                    color: "#3E2E25",
                    lineHeight: 1.55,
                  }}
                >
                  {s.body}
                </div>
              </div>
            ))}

            {sideNoteDraft && (
              <div
                className="p-4 rounded-2xl"
                style={{
                  background: "#FFFFFF",
                  border: "1px solid #C8A47B",
                  boxShadow: "0 8px 24px rgba(70, 49, 34, 0.08)",
                }}
              >
                <div
                  style={{
                    fontFamily: "Inter, sans-serif",
                    fontSize: 11,
                    color: "#9A8677",
                    fontStyle: "italic",
                    marginBottom: 8,
                    paddingLeft: 8,
                    borderLeft: "2px solid #C8A47B",
                  }}
                >
                  "{sideNoteDraft.anchor.length > 60 ? sideNoteDraft.anchor.slice(0, 60) + "…" : sideNoteDraft.anchor}"
                </div>
                <textarea
                  autoFocus
                  value={sideNoteDraft.body}
                  onChange={(e) =>
                    setSideNoteDraft({ ...sideNoteDraft, body: e.target.value })
                  }
                  placeholder="Add your thought..."
                  className="w-full outline-none resize-none bg-transparent"
                  rows={3}
                  style={{
                    fontFamily: "Inter, sans-serif",
                    fontSize: 13,
                    color: "#3E2E25",
                    lineHeight: 1.55,
                  }}
                />
                <div className="flex gap-2 mt-2">
                  <button
                    onClick={saveSideNote}
                    className="px-3 py-1 rounded-full"
                    style={{
                      background: "#705642",
                      color: "#FFFFFF",
                      fontFamily: "Inter, sans-serif",
                      fontSize: 12,
                    }}
                  >
                    Save
                  </button>
                  <button
                    onClick={() => setSideNoteDraft(null)}
                    className="px-3 py-1 rounded-full"
                    style={{
                      background: "transparent",
                      color: "#9A8677",
                      fontFamily: "Inter, sans-serif",
                      fontSize: 12,
                    }}
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

const ToolbarBtn: React.FC<{ icon: React.ReactNode; onClick: () => void; label: string }> = ({
  icon,
  onClick,
  label,
}) => (
  <button
    onClick={onClick}
    title={label}
    className="p-2 rounded-full transition-colors"
    style={{ color: "#5E4C40" }}
    onMouseEnter={(e) => (e.currentTarget.style.background = "#F0E4D3")}
    onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
  >
    {icon}
  </button>
);

// ─────────────────────────────────────────────────────────────
// Manim placeholder — animated SVG so it doesn't feel dead
// ─────────────────────────────────────────────────────────────

const ManimPlaceholder: React.FC<{ topic: AnimatableTopic }> = ({ topic }) => {
  if (topic.id === "merge-sort") {
    return (
      <svg viewBox="0 0 400 200" className="w-full h-full">
        {[5, 2, 8, 1, 9, 3, 7, 4].map((v, i) => (
          <motion.rect
            key={i}
            x={40 + i * 40}
            y={180 - v * 16}
            width={28}
            height={v * 16}
            fill="#705642"
            initial={{ y: 180, height: 0 }}
            animate={{ y: 180 - v * 16, height: v * 16 }}
            transition={{ duration: 0.6, delay: i * 0.1, ease: [0.22, 1, 0.36, 1] }}
            rx={2}
          />
        ))}
        <motion.text
          x={200}
          y={30}
          textAnchor="middle"
          fontFamily="Cormorant Garamond, serif"
          fontStyle="italic"
          fontSize="16"
          fill="#9A8677"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1 }}
        >
          divide → conquer → merge
        </motion.text>
      </svg>
    );
  }
  if (topic.id === "shell-method" || topic.id === "washer-method") {
    return (
      <svg viewBox="0 0 400 200" className="w-full h-full">
        {[0, 1, 2, 3, 4].map((i) => (
          <motion.ellipse
            key={i}
            cx={200}
            cy={100}
            rx={30 + i * 18}
            ry={8 + i * 2}
            fill="none"
            stroke="#C8A47B"
            strokeWidth={1.2}
            initial={{ opacity: 0, scale: 0.5 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5, delay: i * 0.15 }}
          />
        ))}
        <motion.line
          x1={200}
          y1={20}
          x2={200}
          y2={180}
          stroke="#705642"
          strokeWidth={1.5}
          strokeDasharray="4 4"
          initial={{ pathLength: 0 }}
          animate={{ pathLength: 1 }}
          transition={{ duration: 1 }}
        />
      </svg>
    );
  }
  // Generic
  return (
    <div className="flex flex-col items-center gap-3">
      <Sparkles size={32} strokeWidth={1.2} style={{ color: "#C8A47B" }} />
      <p
        style={{
          fontFamily: "'Cormorant Garamond', serif",
          fontStyle: "italic",
          fontSize: 18,
          color: "#705642",
        }}
      >
        {topic.name} animation
      </p>
      <p
        style={{
          fontFamily: "Inter, sans-serif",
          fontSize: 12,
          color: "#9A8677",
        }}
      >
        Manim render goes here
      </p>
    </div>
  );
};

// ─────────────────────────────────────────────────────────────
// Animations gallery
// ─────────────────────────────────────────────────────────────

const AnimationsPage: React.FC<{ topics: AnimatableTopic[] }> = ({ topics }) => {
  const [selected, setSelected] = useState<AnimatableTopic | null>(null);
  const categoryLabels: Record<AnimatableTopic["category"], string> = {
    calculus: "Calculus",
    arithmetic: "Arithmetic",
    dsa: "Data Structures & Algorithms",
    physics: "Physics",
    linalg: "Linear Algebra",
  };
  const grouped = topics.reduce<Record<string, AnimatableTopic[]>>((acc, t) => {
    (acc[t.category] = acc[t.category] || []).push(t);
    return acc;
  }, {});

  return (
    <div className="h-full overflow-auto" style={{ background: "#F5F0EA" }}>
      <div className="max-w-5xl mx-auto px-12 py-16">
        <div className="flex items-center gap-2 mb-2">
          <Sparkle className="w-3 h-3" style={{ color: "#C8A47B" }} />
          <span
            style={{
              fontFamily: "'Cormorant Garamond', serif",
              fontStyle: "italic",
              fontSize: 14,
              color: "#9A8677",
              letterSpacing: "0.05em",
            }}
          >
            Currently animatable
          </span>
        </div>
        <h1
          style={{
            fontFamily: "'Cormorant Garamond', serif",
            fontSize: 56,
            fontWeight: 600,
            color: "#2F261F",
            lineHeight: 1.05,
            letterSpacing: "-0.02em",
            marginBottom: 40,
          }}
        >
          Concepts we can <em>show you.</em>
        </h1>

        {Object.entries(grouped).map(([cat, list]) => (
          <div key={cat} className="mb-12">
            <h2
              style={{
                fontFamily: "Inter, sans-serif",
                fontSize: 12,
                color: "#9A8677",
                letterSpacing: "0.1em",
                textTransform: "uppercase",
                marginBottom: 16,
              }}
            >
              {categoryLabels[cat as AnimatableTopic["category"]]}
            </h2>
            <div className="grid grid-cols-2 gap-4">
              {list.map((t) => (
                <button
                  key={t.id}
                  onClick={() => setSelected(t)}
                  className="text-left p-6 rounded-3xl transition-all relative group"
                  style={{
                    background: "#FFF9F0",
                    border: "1px solid #DED0C2",
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.borderColor = "#C8A47B";
                    e.currentTarget.style.transform = "translateY(-2px)";
                    e.currentTarget.style.boxShadow = "0 12px 40px rgba(70, 49, 34, 0.10)";
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = "#DED0C2";
                    e.currentTarget.style.transform = "translateY(0)";
                    e.currentTarget.style.boxShadow = "none";
                  }}
                >
                  <Sparkle
                    className="absolute top-4 right-4 w-2.5 h-2.5 opacity-0 group-hover:opacity-100 transition-opacity"
                    style={{ color: "#C8A47B" }}
                  />
                  <h3
                    style={{
                      fontFamily: "'Cormorant Garamond', serif",
                      fontSize: 24,
                      fontWeight: 600,
                      color: "#2F261F",
                      marginBottom: 6,
                    }}
                  >
                    {t.name}
                  </h3>
                  <p
                    style={{
                      fontFamily: "Inter, sans-serif",
                      fontSize: 14,
                      color: "#5E4C40",
                      lineHeight: 1.5,
                    }}
                  >
                    {t.description}
                  </p>
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>

      <AnimatePresence>
        {selected && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-8"
            style={{ background: "rgba(47, 38, 31, 0.4)" }}
            onClick={() => setSelected(null)}
          >
            <motion.div
              initial={{ scale: 0.96, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.96, opacity: 0 }}
              transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
              className="rounded-3xl overflow-hidden max-w-2xl w-full"
              style={{
                background: "#FFFFFF",
                boxShadow: "0 18px 48px rgba(70, 49, 34, 0.16)",
              }}
              onClick={(e) => e.stopPropagation()}
            >
              <div
                className="aspect-video"
                style={{ background: "#F5F0EA" }}
              >
                <ManimPlaceholder topic={selected} />
              </div>
              <div className="p-8">
                <h3
                  style={{
                    fontFamily: "'Cormorant Garamond', serif",
                    fontSize: 32,
                    fontWeight: 600,
                    color: "#2F261F",
                    marginBottom: 8,
                  }}
                >
                  {selected.name}
                </h3>
                <p
                  style={{
                    fontFamily: "Inter, sans-serif",
                    fontSize: 15,
                    color: "#5E4C40",
                    lineHeight: 1.6,
                  }}
                >
                  {selected.description}
                </p>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

// ─────────────────────────────────────────────────────────────
// Import Notes page — OCR + Gemini Flash auto-formatting
// ─────────────────────────────────────────────────────────────

const ImportNotesPage: React.FC<{
  onCreateNote: (title: string, contentHtml: string) => void;
  onGoToNotes: () => void;
}> = ({ onCreateNote, onGoToNotes }) => {
  const [dragOver, setDragOver] = useState(false);
  const [status, setStatus] = useState<
    | { kind: "idle" }
    | { kind: "ocr"; filename: string }
    | { kind: "formatting"; filename: string }
    | { kind: "success"; filename: string; title: string; html: string }
    | { kind: "error"; message: string }
  >({ kind: "idle" });
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = async (file: File) => {
    try {
      setStatus({ kind: "ocr", filename: file.name });
      const ocr = await MOCK_ocrFile(file);
      setStatus({ kind: "formatting", filename: file.name });
      const formatted = await MOCK_formatNoteFromText(ocr.text);
      setStatus({
        kind: "success",
        filename: file.name,
        title: formatted.title,
        html: formatted.html,
      });
    } catch (e: any) {
      setStatus({ kind: "error", message: e?.message || "Import failed" });
    }
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  };

  const saveAsNote = () => {
    if (status.kind !== "success") return;
    onCreateNote(status.title, status.html);
    onGoToNotes();
  };

  const isLoading = status.kind === "ocr" || status.kind === "formatting";

  return (
    <div className="h-full overflow-auto" style={{ background: "#F5F0EA" }}>
      <div className="max-w-3xl mx-auto px-12 py-16">
        <div className="flex items-center gap-2 mb-2">
          <Sparkle className="w-3 h-3" style={{ color: "#C8A47B" }} />
          <span
            style={{
              fontFamily: "'Cormorant Garamond', serif",
              fontStyle: "italic",
              fontSize: 14,
              color: "#9A8677",
              letterSpacing: "0.05em",
            }}
          >
            Import notes
          </span>
        </div>
        <h1
          style={{
            fontFamily: "'Cormorant Garamond', serif",
            fontSize: 56,
            fontWeight: 600,
            color: "#2F261F",
            lineHeight: 1.05,
            letterSpacing: "-0.02em",
            marginBottom: 12,
          }}
        >
          Photos, formatted <em>beautifully.</em>
        </h1>
        <p
          style={{
            fontFamily: "Inter, sans-serif",
            fontSize: 17,
            color: "#5E4C40",
            lineHeight: 1.6,
            marginBottom: 40,
          }}
        >
          Upload a PDF or photo of your notes. Gemini Flash will read them, write a title,
          and structure them into proper sections — ready to edit.
        </p>

        {status.kind === "idle" && (
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={onDrop}
            onClick={() => inputRef.current?.click()}
            className="rounded-3xl p-16 text-center cursor-pointer transition-all"
            style={{
              border: `2px dashed ${dragOver ? "#705642" : "#C8A47B"}`,
              background: dragOver ? "#F0E4D3" : "#FFF9F0",
            }}
          >
            <input
              ref={inputRef}
              type="file"
              accept=".pdf,.png,.jpg,.jpeg,.webp"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) handleFile(f);
              }}
            />
            <FileImage size={28} strokeWidth={1.2} className="mx-auto mb-4" style={{ color: "#705642" }} />
            <p
              style={{
                fontFamily: "'Cormorant Garamond', serif",
                fontStyle: "italic",
                fontSize: 22,
                color: "#705642",
                marginBottom: 8,
              }}
            >
              Drop a file here, or click to browse.
            </p>
            <p
              style={{
                fontFamily: "Inter, sans-serif",
                fontSize: 13,
                color: "#9A8677",
              }}
            >
              PDF · PNG · JPG · WEBP
            </p>
          </div>
        )}

        {isLoading && (
          <div
            className="rounded-3xl p-16 text-center"
            style={{ background: "#FFF9F0", border: "1px solid #DED0C2" }}
          >
            <Loader2 size={28} strokeWidth={1.2} className="animate-spin mx-auto mb-4" style={{ color: "#705642" }} />
            <p
              style={{
                fontFamily: "'Cormorant Garamond', serif",
                fontStyle: "italic",
                fontSize: 20,
                color: "#705642",
                marginBottom: 6,
              }}
            >
              {status.kind === "ocr" ? `Reading "${status.filename}"...` : "Structuring your note..."}
            </p>
            <p
              style={{
                fontFamily: "Inter, sans-serif",
                fontSize: 12,
                color: "#9A8677",
              }}
            >
              {status.kind === "ocr" ? "Extracting text" : "Gemini Flash is writing the title and sections"}
            </p>
          </div>
        )}

        {status.kind === "success" && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            className="rounded-3xl p-10"
            style={{ background: "#FFF9F0", border: "1px solid #DED0C2" }}
          >
            <div className="flex items-center gap-2 mb-4">
              <div
                className="w-6 h-6 rounded-full flex items-center justify-center"
                style={{ background: "#7A8B6F" }}
              >
                <Check size={12} strokeWidth={2.5} color="#FFFFFF" />
              </div>
              <span
                style={{
                  fontFamily: "'Cormorant Garamond', serif",
                  fontStyle: "italic",
                  fontSize: 20,
                  color: "#705642",
                }}
              >
                Imported beautifully.
              </span>
            </div>

            <p
              style={{
                fontFamily: "Inter, sans-serif",
                fontSize: 11,
                color: "#9A8677",
                letterSpacing: "0.1em",
                textTransform: "uppercase",
                marginBottom: 6,
              }}
            >
              Title
            </p>
            <h3
              style={{
                fontFamily: "'Cormorant Garamond', serif",
                fontSize: 28,
                fontWeight: 600,
                color: "#2F261F",
                marginBottom: 16,
              }}
            >
              {status.title}
            </h3>

            <p
              style={{
                fontFamily: "Inter, sans-serif",
                fontSize: 11,
                color: "#9A8677",
                letterSpacing: "0.1em",
                textTransform: "uppercase",
                marginBottom: 8,
              }}
            >
              Preview
            </p>
            <div
              className="p-5 rounded-2xl mb-6"
              style={{
                background: "#FFFFFF",
                border: "1px solid #ECE1D6",
                fontFamily: "Inter, sans-serif",
                fontSize: 14,
                color: "#3E2E25",
                lineHeight: 1.6,
                maxHeight: 280,
                overflow: "auto",
              }}
              dangerouslySetInnerHTML={{ __html: status.html }}
            />

            <div className="flex gap-3">
              <button
                onClick={saveAsNote}
                className="px-5 py-2.5 rounded-full"
                style={{
                  background: "#705642",
                  color: "#FFFFFF",
                  fontFamily: "Inter, sans-serif",
                  fontSize: 14,
                  fontWeight: 500,
                }}
              >
                Save as note
              </button>
              <button
                onClick={() => setStatus({ kind: "idle" })}
                className="px-5 py-2.5 rounded-full"
                style={{
                  background: "transparent",
                  border: "1px solid #C8A47B",
                  color: "#705642",
                  fontFamily: "Inter, sans-serif",
                  fontSize: 14,
                  fontWeight: 500,
                }}
              >
                Import another
              </button>
            </div>
          </motion.div>
        )}

        {status.kind === "error" && (
          <ImportError message={status.message} onRetry={() => setStatus({ kind: "idle" })} />
        )}
      </div>
    </div>
  );
};

// ─────────────────────────────────────────────────────────────
// Import Animations page — upload a problem, see it animated
// ─────────────────────────────────────────────────────────────

const ImportAnimationsPage: React.FC<{
  topics: AnimatableTopic[];
}> = ({ topics }) => {
  const [dragOver, setDragOver] = useState(false);
  const [status, setStatus] = useState<
    | { kind: "idle" }
    | { kind: "ocr"; filename: string }
    | { kind: "parsing"; filename: string }
    | { kind: "no-match"; problem: string }
    | { kind: "rendering"; problem: string; topic: AnimatableTopic }
    | { kind: "ready"; problem: string; topic: AnimatableTopic; breakdown: BreakdownSection[] }
    | { kind: "error"; message: string }
  >({ kind: "idle" });
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = async (file: File) => {
    try {
      setStatus({ kind: "ocr", filename: file.name });
      const ocr = await MOCK_ocrFile(file);
      setStatus({ kind: "parsing", filename: file.name });
      const parsed = await MOCK_parseProblem(ocr.text, topics);
      const topic = topics.find((t) => t.id === parsed.topicId) || null;
      if (!topic) {
        setStatus({ kind: "no-match", problem: parsed.problem });
        return;
      }
      setStatus({ kind: "rendering", problem: parsed.problem, topic });
      const [, breakdown] = await Promise.all([
        generateAnimation(topic),
        explainProblem(parsed.problem, topic),
      ]);
      setStatus({ kind: "ready", problem: parsed.problem, topic, breakdown });
    } catch (e: any) {
      setStatus({ kind: "error", message: e?.message || "Import failed" });
    }
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  };

  const isLoading = status.kind === "ocr" || status.kind === "parsing" || status.kind === "rendering";

  const loadingLabel = () => {
    if (status.kind === "ocr") return `Reading "${status.filename}"...`;
    if (status.kind === "parsing") return "Identifying the concept...";
    if (status.kind === "rendering") return `Rendering the ${status.topic.name} animation...`;
    return "";
  };

  const loadingSub = () => {
    if (status.kind === "ocr") return "Extracting text";
    if (status.kind === "parsing") return "Gemini Flash is matching your problem to a topic";
    if (status.kind === "rendering") return "Building the breakdown";
    return "";
  };

  return (
    <div className="h-full overflow-auto" style={{ background: "#F5F0EA" }}>
      <div className="max-w-4xl mx-auto px-12 py-16">
        <div className="flex items-center gap-2 mb-2">
          <Sparkle className="w-3 h-3" style={{ color: "#C8A47B" }} />
          <span
            style={{
              fontFamily: "'Cormorant Garamond', serif",
              fontStyle: "italic",
              fontSize: 14,
              color: "#9A8677",
              letterSpacing: "0.05em",
            }}
          >
            Import a problem
          </span>
        </div>
        <h1
          style={{
            fontFamily: "'Cormorant Garamond', serif",
            fontSize: 56,
            fontWeight: 600,
            color: "#2F261F",
            lineHeight: 1.05,
            letterSpacing: "-0.02em",
            marginBottom: 12,
          }}
        >
          See it <em>move.</em>
        </h1>
        <p
          style={{
            fontFamily: "Inter, sans-serif",
            fontSize: 17,
            color: "#5E4C40",
            lineHeight: 1.6,
            marginBottom: 40,
          }}
        >
          Upload a textbook problem. We'll read it, identify the technique, animate the solution,
          and label which part of the figure represents what.
        </p>

        {status.kind === "idle" && (
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={onDrop}
            onClick={() => inputRef.current?.click()}
            className="rounded-3xl p-16 text-center cursor-pointer transition-all"
            style={{
              border: `2px dashed ${dragOver ? "#705642" : "#C8A47B"}`,
              background: dragOver ? "#F0E4D3" : "#FFF9F0",
            }}
          >
            <input
              ref={inputRef}
              type="file"
              accept=".pdf,.png,.jpg,.jpeg,.webp"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) handleFile(f);
              }}
            />
            <Sparkles size={28} strokeWidth={1.2} className="mx-auto mb-4" style={{ color: "#705642" }} />
            <p
              style={{
                fontFamily: "'Cormorant Garamond', serif",
                fontStyle: "italic",
                fontSize: 22,
                color: "#705642",
                marginBottom: 8,
              }}
            >
              Drop a problem here, or click to browse.
            </p>
            <p
              style={{
                fontFamily: "Inter, sans-serif",
                fontSize: 13,
                color: "#9A8677",
              }}
            >
              PDF · PNG · JPG · WEBP
            </p>
          </div>
        )}

        {isLoading && (
          <div
            className="rounded-3xl p-16 text-center"
            style={{ background: "#FFF9F0", border: "1px solid #DED0C2" }}
          >
            <Loader2 size={28} strokeWidth={1.2} className="animate-spin mx-auto mb-4" style={{ color: "#705642" }} />
            <p
              style={{
                fontFamily: "'Cormorant Garamond', serif",
                fontStyle: "italic",
                fontSize: 20,
                color: "#705642",
                marginBottom: 6,
              }}
            >
              {loadingLabel()}
            </p>
            <p
              style={{
                fontFamily: "Inter, sans-serif",
                fontSize: 12,
                color: "#9A8677",
              }}
            >
              {loadingSub()}
            </p>
          </div>
        )}

        {status.kind === "no-match" && (
          <div
            className="rounded-3xl p-10"
            style={{ background: "#FFF9F0", border: "1px solid #DED0C2" }}
          >
            <p
              style={{
                fontFamily: "'Cormorant Garamond', serif",
                fontStyle: "italic",
                fontSize: 22,
                color: "#705642",
                marginBottom: 12,
              }}
            >
              We couldn't match this to an animatable topic yet.
            </p>
            <p
              style={{
                fontFamily: "Inter, sans-serif",
                fontSize: 14,
                color: "#5E4C40",
                lineHeight: 1.6,
                marginBottom: 16,
              }}
            >
              Here's what we read:
            </p>
            <div
              className="p-4 rounded-2xl mb-6"
              style={{
                background: "#FFFFFF",
                border: "1px solid #ECE1D6",
                fontFamily: "Inter, sans-serif",
                fontSize: 14,
                color: "#3E2E25",
                lineHeight: 1.6,
                whiteSpace: "pre-wrap",
              }}
            >
              {status.problem}
            </div>
            <button
              onClick={() => setStatus({ kind: "idle" })}
              className="px-5 py-2.5 rounded-full"
              style={{
                background: "#705642",
                color: "#FFFFFF",
                fontFamily: "Inter, sans-serif",
                fontSize: 14,
                fontWeight: 500,
              }}
            >
              Try another
            </button>
          </div>
        )}

        {status.kind === "ready" && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            className="rounded-3xl overflow-hidden"
            style={{
              background: "#FFFFFF",
              border: "1px solid #DED0C2",
              boxShadow: "0 12px 40px rgba(70, 49, 34, 0.10)",
            }}
          >
            <div
              className="px-8 py-5 flex items-center justify-between"
              style={{ borderBottom: "1px solid #ECE1D6" }}
            >
              <div className="flex items-center gap-2">
                <Sparkles size={14} strokeWidth={1.5} style={{ color: "#C8A47B" }} />
                <span
                  style={{
                    fontFamily: "'Cormorant Garamond', serif",
                    fontStyle: "italic",
                    fontSize: 20,
                    color: "#705642",
                  }}
                >
                  {status.topic.name}
                </span>
              </div>
              <button
                onClick={() => setStatus({ kind: "idle" })}
                className="px-4 py-1.5 rounded-full"
                style={{
                  background: "transparent",
                  border: "1px solid #C8A47B",
                  color: "#705642",
                  fontFamily: "Inter, sans-serif",
                  fontSize: 12,
                }}
              >
                Import another
              </button>
            </div>

            <div
              className="aspect-video flex items-center justify-center"
              style={{ background: "#F5F0EA" }}
            >
              <ManimPlaceholder topic={status.topic} />
            </div>

            <div className="px-8 py-6">
              <p
                style={{
                  fontFamily: "Inter, sans-serif",
                  fontSize: 11,
                  color: "#9A8677",
                  letterSpacing: "0.1em",
                  textTransform: "uppercase",
                  marginBottom: 8,
                }}
              >
                The problem
              </p>
              <div
                className="p-4 rounded-2xl mb-6"
                style={{
                  background: "#FFF9F0",
                  border: "1px solid #ECE1D6",
                  fontFamily: "Inter, sans-serif",
                  fontSize: 14,
                  color: "#3E2E25",
                  lineHeight: 1.6,
                  whiteSpace: "pre-wrap",
                }}
              >
                {status.problem}
              </div>

              <p
                style={{
                  fontFamily: "Inter, sans-serif",
                  fontSize: 11,
                  color: "#9A8677",
                  letterSpacing: "0.1em",
                  textTransform: "uppercase",
                  marginBottom: 16,
                }}
              >
                Breakdown
              </p>
              {status.breakdown.map((s, i) => (
                <div key={i} className="mb-4 flex gap-4">
                  <div
                    style={{
                      fontFamily: "'Cormorant Garamond', serif",
                      fontStyle: "italic",
                      fontSize: 16,
                      color: "#705642",
                      minWidth: 130,
                    }}
                  >
                    {s.label}
                  </div>
                  <div
                    style={{
                      fontFamily: "Inter, sans-serif",
                      fontSize: 14,
                      color: "#3E2E25",
                      lineHeight: 1.6,
                      flex: 1,
                    }}
                  >
                    {s.body}
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        )}

        {status.kind === "error" && (
          <ImportError message={status.message} onRetry={() => setStatus({ kind: "idle" })} />
        )}
      </div>
    </div>
  );
};

const ImportError: React.FC<{ message: string; onRetry: () => void }> = ({ message, onRetry }) => (
  <div
    className="rounded-3xl p-10"
    style={{ background: "#FFF9F0", border: "1px solid #A65F50" }}
  >
    <p
      style={{
        fontFamily: "'Cormorant Garamond', serif",
        fontStyle: "italic",
        fontSize: 20,
        color: "#A65F50",
        marginBottom: 8,
      }}
    >
      Something went sideways.
    </p>
    <p
      style={{
        fontFamily: "Inter, sans-serif",
        fontSize: 14,
        color: "#5E4C40",
        marginBottom: 16,
      }}
    >
      {message}
    </p>
    <button
      onClick={onRetry}
      className="px-5 py-2.5 rounded-full"
      style={{
        background: "#705642",
        color: "#FFFFFF",
        fontFamily: "Inter, sans-serif",
        fontSize: 14,
      }}
    >
      Try again
    </button>
  </div>
);

// ─────────────────────────────────────────────────────────────
// Root App
// ─────────────────────────────────────────────────────────────

export default function App() {
  const [route, setRoute] = useState<Route>("home");
  const [notes, setNotes] = useState<Note[]>(() => loadNotes());
  const [topics, setTopics] = useState<AnimatableTopic[]>([]);
  const [selectedNoteId, setSelectedNoteId] = useState<string | null>(null);

  // Load topics from "Flask"
  useEffect(() => {
    fetchTopics().then(setTopics);
  }, []);

  // Persist on every notes change
  useEffect(() => {
    saveNotes(notes);
  }, [notes]);

  const createNote = (title = "", contentHtml = "") => {
    const n: Note = {
      id: uid(),
      title,
      contentHtml,
      sideNotes: [],
      tags: [],
      updatedAt: Date.now(),
      createdAt: Date.now(),
    };
    setNotes((prev) => [n, ...prev]);
    setSelectedNoteId(n.id);
    setRoute("notes");
  };

  const updateNote = (note: Note) => {
    setNotes((prev) => prev.map((n) => (n.id === note.id ? note : n)));
  };

  const deleteNote = (id: string) => {
    setNotes((prev) => prev.filter((n) => n.id !== id));
  };

  return (
    <div className="flex h-screen w-screen" style={{ fontFamily: "Inter, sans-serif" }}>
      <Sidebar
        route={route}
        onRoute={setRoute}
        onNewNote={() => createNote()}
      />

      <main className="flex-1 overflow-hidden">
        {route === "home" && <HomePage />}
        {route === "notes" && (
          <NotesPage
            notes={notes}
            topics={topics}
            onUpdate={updateNote}
            onDelete={deleteNote}
            onNew={() => createNote()}
            selectedId={selectedNoteId}
            setSelectedId={setSelectedNoteId}
          />
        )}
        {route === "animations" && <AnimationsPage topics={topics} />}
        {route === "import-notes" && (
          <ImportNotesPage
            onCreateNote={(title, content) => createNote(title, content)}
            onGoToNotes={() => setRoute("notes")}
          />
        )}
        {route === "import-animations" && <ImportAnimationsPage topics={topics} />}
      </main>
    </div>
  );
}
