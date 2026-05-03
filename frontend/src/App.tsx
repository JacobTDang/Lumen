// Lumen — Editorial note-taking app with Manim-style animations.
// Single-file React 18 + TypeScript artifact.
//
// Backend wiring (preserved from prior revision):
//   - GET  VITE_FLASK_URL/topics             -> { topics: AnimatableTopic[] }
//   - POST VITE_FLASK_URL/ask                { question } -> { job_id }
//   - GET  VITE_FLASK_URL/status/{job_id}    -> { status: "pending"|"done"|"error", url?, error? }
//   - POST VITE_FLASK_URL/breakdown          { problem, topicId, topicName, topicDescription }
//                                            -> { sections: BreakdownSection[] }
//
// OCR / Gemini text endpoints (called via the Flask backend, not directly from
// the browser — the Gemini key lives in backend/.env, never in VITE_* vars):
//   - POST /api/ocr             multipart file -> { text }
//   - POST /api/format-note     { rawText } -> { title, html }
//   - POST /api/parse-problem   { rawText, topics } -> { problem, topicId }
// Each falls back to a local heuristic if the backend call fails (typically
// because GEMINI_API_KEY isn't configured).

import React, { useState, useEffect, useRef, useMemo, useCallback } from "react";
import { motion, AnimatePresence, LayoutGroup } from "framer-motion";
import {
  Home,
  FileText,
  Play,
  Upload,
  Search,
  Plus,
  Sparkles,
  Bold,
  Italic,
  Highlighter,
  StickyNote,
  Trash2,
  X,
  Check,
  FileImage,
} from "lucide-react";

// ─────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────

type Route = "home" | "notes" | "animations" | "import-notes" | "import-animations";

interface SideNote {
  id: string;
  anchor: string;
  body: string;
  createdAt: number;
}

interface Note {
  id: string;
  title: string;
  contentHtml: string;
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
// Topic catalogue (used as fallback when /topics is unreachable)
// ─────────────────────────────────────────────────────────────

const MOCK_TOPICS: AnimatableTopic[] = [
  { id: "merge-sort", name: "Merge Sort", category: "dsa",
    keywords: ["merge sort", "mergesort", "divide and conquer sort"],
    description: "Recursive divide-and-merge visualization with comparison highlights." },
  { id: "quick-sort", name: "Quick Sort", category: "dsa",
    keywords: ["quick sort", "quicksort", "partition"],
    description: "Pivot-based partitioning shown step by step." },
  { id: "binary-search", name: "Binary Search", category: "dsa",
    keywords: ["binary search", "log n search"],
    description: "Halving the search space on a sorted array." },
  { id: "chain-rule", name: "Chain Rule", category: "calculus",
    keywords: ["chain rule", "composite derivative", "f(g(x))"],
    description: "Derivative of nested functions, layer by layer." },
  { id: "washer-method", name: "Washer Method", category: "calculus",
    keywords: ["washer method", "volume of revolution", "disk method"],
    description: "Volume of solids of revolution using stacked washers." },
  { id: "shell-method", name: "Cylindrical Shell Method", category: "calculus",
    keywords: ["cylindrical shell", "shell method", "shells"],
    description: "Volume by unwrapping concentric cylindrical shells." },
  { id: "derivative-power-rule", name: "Power Rule", category: "calculus",
    keywords: ["power rule", "derivative of x^n"],
    description: "Why d/dx[x^n] = n·x^(n-1)." },
];

// ─────────────────────────────────────────────────────────────
// Direct topic → backend scene mapping.
//
// The DSA/math LLM planner has its own scene catalog that doesn't 1:1 match
// our user-facing topic catalog. For ambiguous topics it tends to settle on
// the same fallback ("backtracking_subsets / permutations") regardless of
// input, which then gets pinned by the worker's content-hash cache.
//
// Bypass the planner entirely when we already know which scene + params we
// want — call /render directly. Falls back to /ask (LLM planning) for any
// topic not in this map.
// ─────────────────────────────────────────────────────────────

const TOPIC_SCENE_MAP: Record<string, { scene: string; params: Record<string, unknown> }> = {
  "binary-search": {
    scene: "binary_search_index",
    params: { array: [1, 3, 5, 7, 9, 11, 13, 15], algorithm: "find_target", target: 7 },
  },
  "washer-method": {
    scene: "washer_method",
    params: { f_expression: "x**2", g_expression: "0", domain: [0, 2], n_washers: 8 },
  },
  "shell-method": {
    scene: "shell_method",
    params: { expression: "x**2", domain: [0, 2], n_shells: 8 },
  },
  "chain-rule": {
    scene: "tangent_line",
    // Classic chain-rule example: outer u², inner 2x+1.
    // Kept low-degree so the plot renders quickly without big y-ranges.
    params: { expression: "(2*x + 1)**2", x_point: 1, domain: [-2, 2] },
  },
  "derivative-power-rule": {
    scene: "tangent_line",
    params: { expression: "x**3", x_point: 1, domain: [-2, 2] },
  },
  "merge-sort": {
    scene: "merge_sort",
    params: { array: [5, 2, 8, 1, 9, 3, 7, 4] },
  },
  "quick-sort": {
    scene: "quick_sort",
    params: { array: [3, 7, 1, 5, 9, 2, 8, 4] },
  },
};

// Topics whose default array param should be replaced by an array literal
// found in the user's selection (e.g. "quick sort [1,4,6,3,7,8,0]").
const ARRAY_PARAM_TOPICS: Record<string, string> = {
  "merge-sort": "array",
  "quick-sort": "array",
  "binary-search": "array",
};

// Find the first JS-style number array in `text`. Returns null if none, or
// if the parsed array is too short/long to render cleanly.
function extractArray(text: string): number[] | null {
  const m = text.match(/\[\s*(-?\d+(?:\.\d+)?(?:\s*,\s*-?\d+(?:\.\d+)?)*)\s*\]/);
  if (!m) return null;
  const items = m[1].split(",").map((s) => parseFloat(s.trim()));
  if (items.some((n) => !Number.isFinite(n))) return null;
  if (items.length < 2 || items.length > 20) return null;
  return items;
}

// Given a topic and a chunk of text (selection or surrounding paragraph),
// build a sceneOverride that uses any embedded array literal as the topic's
// array param. Returns null if no override is needed.
function arrayOverrideFor(
  topic: AnimatableTopic,
  text: string
): { scene: string; params: Record<string, unknown> } | null {
  const paramName = ARRAY_PARAM_TOPICS[topic.id];
  if (!paramName) return null;
  const arr = extractArray(text);
  const base = TOPIC_SCENE_MAP[topic.id];
  if (!arr || !base) return null;
  return {
    scene: base.scene,
    params: { ...base.params, [paramName]: arr },
  };
}

// ─────────────────────────────────────────────────────────────
// Real backend calls — Flask + Manim service
// ─────────────────────────────────────────────────────────────

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

type AnimResult = { videoUrl: string; status: "ready" | "error"; error?: string };

// Module-level "live" progress map: pollJob writes the latest backend-reported
// progress into this map keyed by topic id, so the React UI can read real
// numbers via the useLiveProgress hook below. Wiped on render completion.
const _liveProgress = new Map<string, number>();
const _liveListeners = new Set<() => void>();
function _emitLive() { _liveListeners.forEach((cb) => cb()); }
function setLiveProgress(topicId: string, value: number | null) {
  if (value === null) _liveProgress.delete(topicId);
  else _liveProgress.set(topicId, value);
  _emitLive();
}
function useLiveProgress(topicId: string | null): number | null {
  const [, force] = useState(0);
  useEffect(() => {
    const cb = () => force((n) => n + 1);
    _liveListeners.add(cb);
    return () => { _liveListeners.delete(cb); };
  }, []);
  if (!topicId) return null;
  return _liveProgress.has(topicId) ? _liveProgress.get(topicId)! : null;
}

const flaskBase = (): string =>
  (import.meta.env.VITE_FLASK_URL as string | undefined) || "http://localhost:5000";

// Poll /status/<job_id> until done/error/timeout. 2-minute deadline matches
// the worker's 180s render budget plus stitch overhead.
async function pollJob(flaskUrl: string, jobId: string, topicId: string): Promise<AnimResult> {
  // Backend's manim subprocess has its own 180s timeout; give the frontend
  // a small grace window beyond that so we always read the backend's final
  // status (done OR error) instead of timing out independently first.
  const deadline = Date.now() + 200_000;
  try {
    while (Date.now() < deadline) {
      await new Promise((r) => setTimeout(r, 350));
      const statusRes = await fetch(`${flaskUrl}/status/${jobId}`);
      if (!statusRes.ok) continue;
      const job = await statusRes.json();
      // Stream real progress to the live-progress map so React components
      // observing this topic re-render with the actual percentage.
      if (typeof job.progress === "number") {
        setLiveProgress(topicId, job.progress);
      }
      if (job.status === "done" && job.url) {
        return { videoUrl: `${flaskUrl}${job.url}`, status: "ready" };
      }
      if (job.status === "error") {
        return {
          videoUrl: `placeholder://${topicId}`,
          status: "error",
          error: job.error || "render failed",
        };
      }
    }
    return {
      videoUrl: `placeholder://${topicId}`,
      status: "error",
      error: "render timed out after 200s",
    };
  } finally {
    setLiveProgress(topicId, null);
  }
}

async function generateAnimation(
  topic: AnimatableTopic,
  extraContext?: string,
  override?: { scene: string; params: Record<string, unknown> }
): Promise<AnimResult> {
  const flaskUrl = flaskBase();

  // Fast path: explicit override (from an inline expression like "4+4"),
  // or a direct scene mapping for a known topic. Either way, skip the LLM
  // planner and hit /render with explicit scene + params — this avoids the
  // planner misrouting to backtracking_subsets when no good match exists.
  const direct = override ?? TOPIC_SCENE_MAP[topic.id];
  if (direct) {
    try {
      const renderRes = await fetch(`${flaskUrl}/render`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          scene: direct.scene,
          // Default caption to topic.name, but let the mapping override it
          // (so e.g. merge-sort can label its bubble_sort fallback honestly).
          params: { caption: topic.name, ...direct.params },
        }),
      });
      if (!renderRes.ok) {
        const detail = await renderRes.text().catch(() => "");
        return {
          videoUrl: `placeholder://${topic.id}`,
          status: "error",
          error: `/render ${renderRes.status}: ${detail.slice(0, 120)}`,
        };
      }
      const { job_id: jobId } = await renderRes.json();
      if (!jobId) {
        return {
          videoUrl: `placeholder://${topic.id}`,
          status: "error",
          error: "/render returned no job_id",
        };
      }
      return await pollJob(flaskUrl, jobId, topic.id);
    } catch (e) {
      return {
        videoUrl: `placeholder://${topic.id}`,
        status: "error",
        error: e instanceof Error ? e.message : String(e),
      };
    }
  }

  // Slow path: ask the LLM planner. Used for topics with no direct mapping.
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
      return {
        videoUrl: `placeholder://${topic.id}`,
        status: "error",
        error: `/ask ${askRes.status}: ${detail.slice(0, 120)}`,
      };
    }
    const { job_id: jobId } = await askRes.json();
    if (!jobId) {
      return {
        videoUrl: `placeholder://${topic.id}`,
        status: "error",
        error: "/ask returned no job_id",
      };
    }
    return await pollJob(flaskUrl, jobId, topic.id);
  } catch (e) {
    return {
      videoUrl: `placeholder://${topic.id}`,
      status: "error",
      error: e instanceof Error ? e.message : String(e),
    };
  }
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
    { label: "Formula", body: `See the animation for the ${topic.name} formula and visual intuition.` },
    { label: "Example", body: problem.trim() || `A typical ${topic.name} problem.` },
    { label: "Answer",  body: topic.description },
  ];
}

// ─────────────────────────────────────────────────────────────
// OCR + Gemini text endpoints (call backend; fall back to local heuristics
// if the call fails — typically because GEMINI_API_KEY isn't configured).
// ─────────────────────────────────────────────────────────────

async function ocrFile(file: File): Promise<{ text: string }> {
  const flaskUrl = flaskBase();
  const fd = new FormData();
  fd.append("file", file);
  try {
    const res = await fetch(`${flaskUrl}/api/ocr`, { method: "POST", body: fd });
    if (!res.ok) {
      const detail = await res.text().catch(() => "");
      throw new Error(`/api/ocr ${res.status}: ${detail.slice(0, 200)}`);
    }
    const data = await res.json();
    if (typeof data.text !== "string") throw new Error("/api/ocr: missing text field");
    return { text: data.text };
  } catch (e) {
    console.warn("OCR fell back to mock:", e);
    return {
      text: `[Mock OCR output from ${file.name}]\n\nFind the volume of the solid generated by revolving the region bounded by y = x², y = 0, and x = 2 about the y-axis.\n\n(Backend /api/ocr is unreachable — set GEMINI_API_KEY in backend/.env and restart the server.)`,
    };
  }
}

async function formatNoteFromText(rawText: string): Promise<{ title: string; html: string }> {
  const flaskUrl = flaskBase();
  try {
    const res = await fetch(`${flaskUrl}/api/format-note`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ rawText }),
    });
    if (!res.ok) {
      const detail = await res.text().catch(() => "");
      throw new Error(`/api/format-note ${res.status}: ${detail.slice(0, 200)}`);
    }
    const data = await res.json();
    if (typeof data.title === "string" && typeof data.html === "string") {
      return { title: data.title, html: data.html };
    }
    throw new Error("/api/format-note: malformed response");
  } catch (e) {
    console.warn("format-note fell back to mock:", e);
    const lines = rawText.split("\n").filter((l) => l.trim());
    const title = lines[0]?.slice(0, 60) || "Imported note";
    const body = lines.slice(1).map((l) => `<p>${l}</p>`).join("");
    return {
      title: title.replace(/^\[.*?\]\s*/, "").trim() || "Imported note",
      html:
        `<h2>Summary</h2><p>${rawText.split("\n\n")[0]?.slice(0, 200) || ""}</p>` +
        `<h2>Full content</h2>${body}`,
    };
  }
}

async function parseProblem(
  rawText: string,
  topics: AnimatableTopic[]
): Promise<{ problem: string; topicId: string | null }> {
  const flaskUrl = flaskBase();
  try {
    const res = await fetch(`${flaskUrl}/api/parse-problem`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ rawText, topics }),
    });
    if (!res.ok) {
      const detail = await res.text().catch(() => "");
      throw new Error(`/api/parse-problem ${res.status}: ${detail.slice(0, 200)}`);
    }
    const data = await res.json();
    if (typeof data.problem !== "string") throw new Error("/api/parse-problem: missing problem");
    return {
      problem: data.problem,
      topicId: typeof data.topicId === "string" ? data.topicId : null,
    };
  } catch (e) {
    console.warn("parse-problem fell back to mock:", e);
    const matched = findMatchingTopic(rawText, topics);
    return {
      problem: rawText.replace(/^\[.*?\]\s*/, "").trim(),
      topicId: matched?.id || null,
    };
  }
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
// Animation result cache — module-level so it survives note switches.
// Keyed by (topicId, normalized context). Failures are cached too, so
// re-clicking a broken render returns instantly instead of re-rendering;
// the user has to hit "Re-render" to actually retry.
// ─────────────────────────────────────────────────────────────

type CachedAnim = { videoUrl?: string; error?: string; sections: BreakdownSection[] };
const animCache = new Map<string, CachedAnim>();
const cacheKey = (topicId: string, context: string) =>
  `${topicId}::${context.slice(0, 200).trim().toLowerCase()}`;

// ─────────────────────────────────────────────────────────────
// contenteditable caret save/restore by character offset.
// Survives DOM mutation (e.g. when we wrap topic keywords in <span>).
// ─────────────────────────────────────────────────────────────

function getCaretOffset(el: HTMLElement): number | null {
  const sel = window.getSelection();
  if (!sel || sel.rangeCount === 0) return null;
  const range = sel.getRangeAt(0);
  if (!el.contains(range.startContainer)) return null;
  const pre = range.cloneRange();
  pre.selectNodeContents(el);
  pre.setEnd(range.startContainer, range.startOffset);
  return pre.toString().length;
}

function setCaretOffset(el: HTMLElement, offset: number): void {
  const sel = window.getSelection();
  if (!sel) return;
  const range = document.createRange();
  let remaining = offset;
  const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
  let node: Node | null;
  while ((node = walker.nextNode())) {
    const len = node.nodeValue?.length ?? 0;
    if (remaining <= len) {
      range.setStart(node, remaining);
      range.collapse(true);
      sel.removeAllRanges();
      sel.addRange(range);
      return;
    }
    remaining -= len;
  }
  // Past the end: collapse to end of editor
  range.selectNodeContents(el);
  range.collapse(false);
  sel.removeAllRanges();
  sel.addRange(range);
}

// ─────────────────────────────────────────────────────────────
// Decorate topic keywords inline. Walks text nodes, wraps matches in
// <span class="topic-hint" data-topic-id="...">. Idempotent: unwraps
// any existing hints before re-wrapping, so it's safe to re-run.
// ─────────────────────────────────────────────────────────────

function escapeRegex(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

// Unicode superscripts (x², x³, …) → ASCII (x^2, x^3) so sympy can parse it.
// Run this on selected text *before* any regex matching that cares about ^.
function normalizeUnicodeMath(s: string): string {
  const supMap: Record<string, string> = {
    "⁰":"0","¹":"1","²":"2","³":"3","⁴":"4","⁵":"5","⁶":"6","⁷":"7","⁸":"8","⁹":"9",
  };
  let out = "";
  let inSup = false;
  for (const ch of s) {
    if (supMap[ch]) {
      if (!inSup) { out += "^"; inSup = true; }
      out += supMap[ch];
    } else {
      inSup = false;
      out += ch;
    }
  }
  // Common Unicode operator → ASCII
  return out
    .replace(/[−–]/g, "-")   // various dashes → minus
    .replace(/×/g, "*")
    .replace(/÷/g, "/")
    .replace(/√/g, "sqrt");
}

// ─────────────────────────────────────────────────────────────
// Expression detection — turn arbitrary highlighted text like "4+4",
// "7×8", "f(x) = x^2 + 3x" into a renderable scene + params. Distinct
// from the topic catalog: this runs on the actual mathematical content
// the user wrote, not pre-defined keywords.
// ─────────────────────────────────────────────────────────────

type ExpressionHit = {
  scene: string;
  params: Record<string, unknown>;
  displayName: string;        // shown in animation panel header
  matchedText: string;        // exact substring matched (for cache key + inline span)
};

// Detect a single expression in standalone text (used by the selection toolbar).
function detectExpression(text: string): ExpressionHit | null {
  const tRaw = text.trim();
  if (!tRaw) return null;
  // Normalize Unicode (², ³, ×, ÷, √, em dash) so all downstream matchers
  // and sympy can read what the user actually typed.
  const t = normalizeUnicodeMath(tRaw);

  // 0a. Average rate of change patterns: secant line through the endpoints
  //     of an interval. Catches:
  //       "average rate of change of f(x) = x^2 + 1 on the interval [2, 5]"
  //       "average rate of change of x^3 from 1 to 4"
  //       "secant slope of sin(x) on [0, pi]"
  const secantMatch = t.match(
    /(?:average\s+(?:rate\s+of\s+change|slope)|secant\s+(?:slope|line))\s+of\s+(.+?)\s+(?:on\s+(?:the\s+)?(?:interval\s+)?\[\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*\]|from\s+(-?\d+(?:\.\d+)?)\s+to\s+(-?\d+(?:\.\d+)?))/i
  );
  if (secantMatch) {
    let exprRaw = secantMatch[1].trim();
    exprRaw = exprRaw.replace(/^(?:y|f\s*\(\s*x\s*\))\s*=\s*/i, "").replace(/[.,;:]+$/, "");
    const a = parseFloat(secantMatch[2] ?? secantMatch[4]);
    const b = parseFloat(secantMatch[3] ?? secantMatch[5]);
    if (/x/i.test(exprRaw) && Number.isFinite(a) && Number.isFinite(b) && a !== b) {
      const lo = Math.min(a, b), hi = Math.max(a, b);
      const margin = Math.max(1, (hi - lo) * 0.4);
      return {
        scene: "secant_line",
        params: {
          expression: exprRaw.replace(/\^/g, "**"),
          a: lo,
          b: hi,
          domain: [lo - margin, hi + margin],
        },
        displayName: `avg rate of ${exprRaw} on [${lo}, ${hi}]`,
        matchedText: tRaw,
      };
    }
  }

  // 0b. Instantaneous rate of change / derivative / slope at a single point.
  //     Routes to tangent_line.
  const tangentMatch = t.match(
    /(?:instantaneous\s+)?(?:rate\s+of\s+change|derivative|slope)\s+of\s+(.+?)\s+at\s+(?:x\s*=\s*)?(-?\d+(?:\.\d+)?)/i
  );
  if (tangentMatch) {
    let exprRaw = tangentMatch[1].trim();
    exprRaw = exprRaw.replace(/^(?:y|f\s*\(\s*x\s*\))\s*=\s*/i, "").replace(/[.,;:]+$/, "");
    const xPoint = parseFloat(tangentMatch[2]);
    if (/x/i.test(exprRaw) && Number.isFinite(xPoint)) {
      const half = Math.max(2, Math.abs(xPoint) + 2);
      return {
        scene: "tangent_line",
        params: {
          expression: exprRaw.replace(/\^/g, "**"),
          x_point: xPoint,
          domain: [xPoint - half, xPoint + half],
        },
        displayName: `d/dx[${exprRaw}] at x=${xPoint}`,
        matchedText: tRaw,
      };
    }
  }

  // 1. Simple binary arithmetic: "4+4", "12-5", "7×8", "20/4"
  const arith = t.match(/^(-?\d+(?:\.\d+)?)\s*([+\-*/×÷])\s*(-?\d+(?:\.\d+)?)$/);
  if (arith) {
    const a = parseFloat(arith[1]);
    const op = arith[2];
    const b = parseFloat(arith[3]);
    return arithToHit(a, op, b, t);
  }

  // 2. Function definition: "y = ..." or "f(x) = ..."
  const funcEq = t.match(/^(?:y|f\s*\(\s*x\s*\))\s*=\s*(.+)$/i);
  if (funcEq) {
    const raw = funcEq[1].trim();
    if (raw.toLowerCase().includes("x")) {
      return {
        scene: "function_plot",
        params: { expression: raw.replace(/\^/g, "**"), domain: [-5, 5] },
        displayName: `f(x) = ${raw}`,
        matchedText: t,
      };
    }
  }

  // 3. Compound arithmetic: "4*4+1", "2+3*4", "(5-1)*2 + 7".
  //
  // Strategy: split at the first top-level + or - (respecting parens),
  // evaluate each side with PEMDAS, animate as number_line addition or
  // subtraction. Multiplication-only expressions fall through (already
  // covered by the single-binary-op branch above for the simple case).
  {
    const clean = t.replace(/×/g, "*").replace(/÷/g, "/");
    if (/^[\d\s+\-*/().]+$/.test(clean)) {
      const splitIdx = topLevelAddSubIdx(clean);
      if (splitIdx > 0) {
        const op = clean[splitIdx];
        const left = clean.slice(0, splitIdx).trim();
        const a = safeEvalArithmetic(left);
        const total = safeEvalArithmetic(clean);
        if (a !== null && total !== null) {
          const round = (n: number) =>
            Math.abs(n - Math.round(n)) < 1e-9 ? Math.round(n) : n;
          const aR = round(a);
          const totalR = round(total);
          // Recover the second value from the full result, so chained
          // subtractions like "10-3-2" still animate as 10 − 5 (= 5),
          // not 10 − 1 (which is what "left, right=safeEval('3-2')") gives.
          const delta = op === "+" ? totalR - aR : aR - totalR;
          const lo = Math.floor(Math.min(0, aR, totalR)) - 1;
          const hi = Math.ceil(Math.max(0, aR, totalR)) + 1;
          return {
            scene: "number_line",
            params: {
              mode: op === "+" ? "addition" : "subtraction",
              values: [aR, Math.abs(delta)],
              domain: [lo, hi],
            },
            displayName: t.trim(),
            matchedText: t,
          };
        }
      }
    }
  }

  // 4. Bare polynomial in x — e.g. "x^2 + 3x - 2"
  if (/^[\d\s+\-*/^().x]+$/i.test(t) && /x/i.test(t) && !/^\d+$/.test(t)) {
    return {
      scene: "function_plot",
      params: { expression: t.replace(/\^/g, "**"), domain: [-5, 5] },
      displayName: t,
      matchedText: t,
    };
  }

  return null;
}

// Evaluate a strict arithmetic expression. Input must already be sanitized
// to digits, operators, parens, decimal point, and whitespace — Function()
// is otherwise unsafe. Returns null on parse failure or non-finite result.
function safeEvalArithmetic(expr: string): number | null {
  if (!/^[\d\s+\-*/().]+$/.test(expr) || !expr.trim()) return null;
  try {
    // eslint-disable-next-line no-new-func
    const out = Function(`"use strict"; return (${expr})`)();
    return typeof out === "number" && Number.isFinite(out) ? out : null;
  } catch {
    return null;
  }
}

// Find the first top-level + or - in `expr` (depth 0), skipping unary signs
// and operators that follow other operators. Returns -1 if none found.
// Last-resort detector: does this look like math at all? Anything that
// passes goes through the LLM planner (slow path), so we want a permissive
// but not totally credulous filter — accept anything number-y, symbol-y,
// or with a math keyword; reject plain prose like "blah blah".
const _MATH_KEYWORDS = [
  // calculus — concepts + common phrases
  "limit", "derivative", "differentiate", "integral", "integrate",
  "antiderivative", "tangent", "secant", "asymptote", "concavity",
  "concave", "convex", "inflection", "instantaneous", "rate of change",
  "average rate", "slope", "velocity", "acceleration", "approach",
  "approximate", "approximation", "maximum", "minimum", "extremum",
  "extrema", "critical point", "optimization", "related rates",
  "chain rule", "product rule", "quotient rule", "power rule",
  // algebra / pre-calc
  "polynomial", "quadratic", "cubic", "exponential", "logarithm",
  "factor", "expand", "simplify", "inequality", "absolute value",
  "coefficient", "intercept", "y-intercept", "x-intercept", "vertex",
  "root", "zero", "discriminant", "domain", "range",
  // trig
  "sin", "cos", "tan", "sec", "csc", "cot", "sine", "cosine", "tangent",
  "radian", "degree", "amplitude", "period", "phase",
  // analysis
  "sum", "series", "sequence", "convergent", "divergent", "convergence",
  "divergence", "continuous", "discontinuous", "monotonic", "monotonically",
  "infinity", "infinite", "bounded",
  // linear algebra
  "matrix", "vector", "determinant", "eigenvalue", "eigenvector",
  "transpose", "dot product", "cross product", "linear",
  // discrete / combinatorics
  "permutation", "combination", "factorial", "modulo", "prime",
  // geometry
  "triangle", "circle", "polygon", "perimeter", "circumference",
  "hypotenuse", "area", "volume", "surface area", "angle", "radius",
  "diameter", "diagonal",
  // statistics / probability
  "mean", "median", "mode", "variance", "deviation", "probability",
  "expected value", "distribution",
  // common verbs the LLM planner can act on
  "function", "equation", "graph", "plot", "solve", "compute", "evaluate",
  "find the", "calculate", "determine", "estimate", "prove",
];
const _MATH_SYMBOLS = /[∫∑∏≤≥≠πθ∞±√∂∇·×÷^=<>]/;

function isLikelyMath(text: string): boolean {
  const t = text.trim();
  if (!t) return false;

  // Numbers + at least one operator-ish character (catches "4+4", "x = 5",
  // "n^2", "f(2)") — but NOT bare digits in prose like "I have 5 apples".
  if (/\d/.test(t) && /[+\-*/=^<>()]/.test(t)) return true;

  // Math symbols / Unicode ops
  if (_MATH_SYMBOLS.test(t)) return true;

  // Math keyword (whole-word match, case-insensitive)
  const lower = t.toLowerCase();
  for (const kw of _MATH_KEYWORDS) {
    if (new RegExp(`\\b${kw}\\b`, "i").test(lower)) return true;
  }

  // Function-call notation: f(x), g(t), sin(2x), etc.
  if (/\b[a-z]\s*\(\s*[^)]+\s*\)/i.test(t)) return true;

  return false;
}

function topLevelAddSubIdx(expr: string): number {
  let depth = 0;
  for (let i = 0; i < expr.length; i++) {
    const ch = expr[i];
    if (ch === "(") depth++;
    else if (ch === ")") depth--;
    else if (depth === 0 && (ch === "+" || ch === "-") && i > 0) {
      let j = i - 1;
      while (j >= 0 && /\s/.test(expr[j])) j--;
      if (j < 0) continue;                     // operator at start → unary
      const prev = expr[j];
      if ("+-*/(".includes(prev)) continue;    // follows another op → unary
      return i;
    }
  }
  return -1;
}

function arithToHit(a: number, op: string, b: number, raw: string): ExpressionHit | null {
  if (op === "+" || op === "-") {
    const result = op === "+" ? a + b : a - b;
    const lo = Math.floor(Math.min(0, a, result)) - 1;
    const hi = Math.ceil(Math.max(0, a, result)) + 1;
    return {
      scene: "number_line",
      params: {
        mode: op === "+" ? "addition" : "subtraction",
        values: [a, b],
        domain: [lo, hi],
      },
      displayName: `${a} ${op === "+" ? "+" : "−"} ${b}`,
      matchedText: raw,
    };
  }
  // Multiplication: area_model only handles small positive integers nicely.
  if ((op === "*" || op === "×") &&
      Number.isInteger(a) && Number.isInteger(b) && a > 0 && b > 0 && a <= 12 && b <= 12) {
    return {
      scene: "area_model",
      params: { mode: "integer", a: String(a), b: String(b) },
      displayName: `${a} × ${b}`,
      matchedText: raw,
    };
  }
  // Division: no good direct scene — let the LLM fallback handle it
  // (return null so detection misses and toolbar falls through).
  return null;
}

// Find ALL inline expression matches in a text snippet (for auto-highlighting).
// Currently scoped to simple binary arithmetic — function definitions are too
// noisy to auto-detect inline (you can still highlight + select them manually).
function findExpressionMatches(text: string): { idx: number; len: number; hit: ExpressionHit }[] {
  const out: { idx: number; len: number; hit: ExpressionHit }[] = [];
  // Looser match than detectExpression (no anchors) — only integers, since
  // decimals inline are nearly always part of a sentence ("3.4 grams of...").
  const re = /(?<![A-Za-z\d.])(-?\d{1,4})\s*([+\-*/×÷])\s*(-?\d{1,4})(?![A-Za-z\d.])/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(text)) !== null) {
    const a = parseInt(m[1], 10);
    const b = parseInt(m[3], 10);
    const hit = arithToHit(a, m[2], b, m[0]);
    if (hit) out.push({ idx: m.index, len: m[0].length, hit });
  }
  return out;
}

// Module-level cache of expression hits keyed by the matched text snippet —
// the DOM stores only `data-expr-key` so we don't have to JSON-encode params
// onto each span. Cleaned up implicitly by garbage collection of the keys.
const exprHitCache = new Map<string, ExpressionHit>();
const exprKey = (hit: ExpressionHit) => `${hit.scene}|${hit.matchedText}`;

function decorateTopicHints(root: HTMLElement, topics: AnimatableTopic[]): void {
  // Unwrap stale hints first so removed text doesn't keep its decoration.
  root.querySelectorAll("span.topic-hint, span.expr-hint").forEach((el) => {
    const parent = el.parentNode;
    if (!parent) return;
    while (el.firstChild) parent.insertBefore(el.firstChild, el);
    parent.removeChild(el);
  });
  root.normalize();

  // Flatten topic keywords (longest first so multi-word matches win).
  const flat: { kw: string; topicId: string }[] = [];
  topics.forEach((t) => t.keywords.forEach((kw) => flat.push({ kw, topicId: t.id })));
  flat.sort((a, b) => b.kw.length - a.kw.length);
  const topicRe = flat.length
    ? new RegExp(`(${flat.map((f) => escapeRegex(f.kw)).join("|")})`, "gi")
    : null;
  const keywordToTopic = new Map<string, string>();
  flat.forEach((f) => {
    if (!keywordToTopic.has(f.kw.toLowerCase())) keywordToTopic.set(f.kw.toLowerCase(), f.topicId);
  });

  // Collect text nodes (snapshot — we'll mutate the tree as we go).
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  const textNodes: Text[] = [];
  let cur: Node | null;
  while ((cur = walker.nextNode())) textNodes.push(cur as Text);

  for (const node of textNodes) {
    const text = node.nodeValue ?? "";
    if (!text) continue;

    // Collect topic keyword matches
    type Match =
      | { idx: number; len: number; kind: "topic"; topicId: string }
      | { idx: number; len: number; kind: "expr"; key: string };
    const matches: Match[] = [];

    if (topicRe) {
      topicRe.lastIndex = 0;
      let m: RegExpExecArray | null;
      while ((m = topicRe.exec(text)) !== null) {
        const tid = keywordToTopic.get(m[1].toLowerCase());
        if (tid) matches.push({ idx: m.index, len: m[1].length, kind: "topic", topicId: tid });
      }
    }

    // Collect expression matches
    for (const e of findExpressionMatches(text)) {
      const key = exprKey(e.hit);
      exprHitCache.set(key, e.hit);
      matches.push({ idx: e.idx, len: e.len, kind: "expr", key });
    }

    if (!matches.length) continue;

    // Sort by start index, drop any later match that overlaps an earlier one.
    matches.sort((a, b) => a.idx - b.idx || b.len - a.len);
    const kept: Match[] = [];
    let endSoFar = -1;
    for (const mm of matches) {
      if (mm.idx >= endSoFar) {
        kept.push(mm);
        endSoFar = mm.idx + mm.len;
      }
    }

    const frag = document.createDocumentFragment();
    let last = 0;
    for (const mm of kept) {
      if (mm.idx > last) frag.appendChild(document.createTextNode(text.slice(last, mm.idx)));
      const span = document.createElement("span");
      if (mm.kind === "topic") {
        span.className = "topic-hint";
        span.dataset.topicId = mm.topicId;
      } else {
        span.className = "expr-hint";
        span.dataset.exprKey = mm.key;
      }
      span.textContent = text.slice(mm.idx, mm.idx + mm.len);
      frag.appendChild(span);
      last = mm.idx + mm.len;
    }
    if (last < text.length) frag.appendChild(document.createTextNode(text.slice(last)));
    node.parentNode?.replaceChild(frag, node);
  }
}

// ─────────────────────────────────────────────────────────────
// Decorative stubs (the new dark theme drops the botanical accents)
// ─────────────────────────────────────────────────────────────

const BotanicalAccent: React.FC<{ className?: string; style?: React.CSSProperties }> = () => null;
const Sparkle: React.FC<{ className?: string; style?: React.CSSProperties }> = () => null;

// ─────────────────────────────────────────────────────────────
// Design tokens — keep magic numbers in one place
// ─────────────────────────────────────────────────────────────

const C = {
  bg: "#1A1A1A",
  surface: "#242424",
  surfaceHi: "#2A2A2A",
  border: "#26262A",
  borderSoft: "#1F1F23",
  borderAlt: "#2A2A2A",
  text: "#E8E8E8",
  textMuted: "#A0A0A0",
  textFaint: "#6B6B6B",
  accent: "#2563EB",
  accentText: "#FFFFFF",
  warning: "#F5D45C",
  danger: "#A65F50",
  ok: "#7A8B6F",
  highlight: "rgba(255, 235, 100, 0.28)",
};

const SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif";
const BODY = "Inter, sans-serif";
const EASE: [number, number, number, number] = [0.22, 1, 0.36, 1];

// ─────────────────────────────────────────────────────────────
// Sidebar — LayoutGroup gives the active row a sliding pill
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
      style={{ width: 220, background: C.bg, borderColor: C.borderAlt }}
    >
      <div className="px-4 pt-5 pb-4 flex items-center gap-2">
        <span style={{ fontSize: 15, fontWeight: 600, color: C.text, letterSpacing: "-0.01em" }}>
          Lumen
        </span>
      </div>

      <motion.button
        onClick={onNewNote}
        whileHover={{ background: C.surface }}
        whileTap={{ scale: 0.97 }}
        transition={{ duration: 0.15 }}
        className="mx-2 mb-3 px-3 py-1.5 rounded-md flex items-center gap-2"
        style={{
          background: "transparent",
          color: C.textMuted,
          fontFamily: BODY,
          fontSize: 13,
          fontWeight: 400,
        }}
      >
        <Plus size={14} strokeWidth={1.8} />
        New note
      </motion.button>

      <div
        className="px-4 pt-2 pb-1"
        style={{ fontSize: 11, fontWeight: 500, color: C.textFaint, letterSpacing: "0.02em" }}
      >
        Pages
      </div>

      <LayoutGroup>
        <nav className="px-2 flex-1">
          {items.map((it) => {
            const active = route === it.key;
            return (
              <button
                key={it.key}
                onClick={() => onRoute(it.key)}
                className="w-full px-3 py-1.5 mb-0.5 rounded-md flex items-center gap-2.5 text-left relative"
                style={{
                  color: active ? C.text : C.textMuted,
                  fontFamily: BODY,
                  fontSize: 13,
                  fontWeight: active ? 500 : 400,
                  background: "transparent",
                  transition: "color 180ms ease",
                }}
                onMouseEnter={(e) => {
                  if (!active) e.currentTarget.style.background = C.surface;
                }}
                onMouseLeave={(e) => {
                  if (!active) e.currentTarget.style.background = "transparent";
                }}
              >
                {active && (
                  <motion.div
                    layoutId="sidebar-active-pill"
                    className="absolute inset-0 rounded-md"
                    style={{ background: "#2F2F2F", zIndex: 0 }}
                    transition={{ type: "spring", stiffness: 380, damping: 32 }}
                  />
                )}
                <span className="relative z-10 flex items-center gap-2.5">
                  {it.icon}
                  {it.label}
                </span>
              </button>
            );
          })}
        </nav>
      </LayoutGroup>
    </aside>
  );
};

// ─────────────────────────────────────────────────────────────
// Home page
// ─────────────────────────────────────────────────────────────

const HomePage: React.FC<{
  notes: Note[];
  topicCount: number;
  onRoute: (r: Route) => void;
  onNewNote: () => void;
  onOpenNote: (id: string) => void;
}> = ({ notes, topicCount, onRoute, onNewNote, onOpenNote }) => {
  const recent = useMemo(
    () => [...notes].sort((a, b) => b.updatedAt - a.updatedAt).slice(0, 4),
    [notes]
  );

  const actions: {
    title: string;
    body: string;
    icon: React.ReactNode;
    onClick: () => void;
  }[] = [
    {
      title: "New note",
      body: "Start writing. Highlight a concept to bring it to life.",
      icon: <Plus size={18} strokeWidth={1.6} />,
      onClick: onNewNote,
    },
    {
      title: "Import notes",
      body: "Photograph or PDF your notes — we'll structure them for you.",
      icon: <FileImage size={18} strokeWidth={1.6} />,
      onClick: () => onRoute("import-notes"),
    },
    {
      title: "Browse animations",
      body: `${topicCount} topic${topicCount === 1 ? "" : "s"} we can show you, end-to-end.`,
      icon: <Play size={18} strokeWidth={1.6} />,
      onClick: () => onRoute("animations"),
    },
  ];

  return (
    <div className="h-full overflow-auto" style={{ background: C.bg }}>
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45, ease: EASE }}
        className="max-w-4xl mx-auto px-12 py-16"
      >
        {/* Hero */}
        <h1
          style={{
            fontFamily: SANS,
            fontSize: 36,
            fontWeight: 600,
            color: C.text,
            letterSpacing: "-0.02em",
            marginBottom: 12,
          }}
        >
          Welcome to Lumen
        </h1>
        <p style={{ fontSize: 16, color: C.textMuted, lineHeight: 1.6, marginBottom: 40, maxWidth: 560 }}>
          A note-taking workspace where any concept you write can be animated.
          Highlight a topic, an expression, or a problem — and watch it move.
        </p>

        {/* Quick actions */}
        <p
          style={{
            fontFamily: BODY,
            fontSize: 11,
            color: C.textFaint,
            letterSpacing: "0.1em",
            textTransform: "uppercase",
            marginBottom: 12,
          }}
        >
          Get started
        </p>
        <div className="grid grid-cols-3 gap-3 mb-12">
          {actions.map((a, i) => (
            <motion.button
              key={a.title}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.08 + i * 0.05, duration: 0.32, ease: EASE }}
              whileHover={{ y: -2, borderColor: C.accent }}
              whileTap={{ scale: 0.985 }}
              onClick={a.onClick}
              className="text-left p-5 rounded-2xl"
              style={{
                background: C.surface,
                border: `1px solid ${C.borderAlt}`,
                color: C.text,
              }}
            >
              <div className="flex items-center gap-2 mb-2" style={{ color: C.accent }}>
                {a.icon}
                <span style={{ fontFamily: SANS, fontSize: 16, fontWeight: 600, color: C.text }}>
                  {a.title}
                </span>
              </div>
              <p style={{ fontFamily: BODY, fontSize: 13, color: C.textMuted, lineHeight: 1.5 }}>
                {a.body}
              </p>
            </motion.button>
          ))}
        </div>

        {/* Recent notes */}
        <div className="flex items-baseline justify-between mb-3">
          <p
            style={{
              fontFamily: BODY,
              fontSize: 11,
              color: C.textFaint,
              letterSpacing: "0.1em",
              textTransform: "uppercase",
            }}
          >
            Recent notes
          </p>
          {notes.length > 0 && (
            <button
              onClick={() => onRoute("notes")}
              style={{
                fontFamily: BODY,
                fontSize: 12,
                color: C.textMuted,
                background: "transparent",
              }}
              onMouseEnter={(e) => (e.currentTarget.style.color = C.accent)}
              onMouseLeave={(e) => (e.currentTarget.style.color = C.textMuted)}
            >
              See all →
            </button>
          )}
        </div>

        {recent.length === 0 ? (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3, duration: 0.3 }}
            className="rounded-2xl p-8 text-center"
            style={{ background: C.surface, border: `1px dashed ${C.borderAlt}` }}
          >
            <p style={{ fontFamily: BODY, fontStyle: "italic", fontSize: 16, color: C.textFaint, marginBottom: 12 }}>
              Your first thought belongs here.
            </p>
            <motion.button
              onClick={onNewNote}
              whileHover={{ scale: 1.03 }}
              whileTap={{ scale: 0.97 }}
              className="px-4 py-2 rounded-full"
              style={{
                background: C.accent,
                color: C.accentText,
                fontFamily: BODY,
                fontSize: 13,
                fontWeight: 500,
              }}
            >
              Create note
            </motion.button>
          </motion.div>
        ) : (
          <div className="grid grid-cols-2 gap-3">
            {recent.map((n, i) => {
              const preview = n.contentHtml.replace(/<[^>]+>/g, " ").trim().slice(0, 100);
              return (
                <motion.button
                  key={n.id}
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.2 + i * 0.04, duration: 0.3, ease: EASE }}
                  whileHover={{ y: -1, borderColor: C.accent }}
                  whileTap={{ scale: 0.99 }}
                  onClick={() => onOpenNote(n.id)}
                  className="text-left p-4 rounded-2xl"
                  style={{ background: C.surface, border: `1px solid ${C.borderAlt}` }}
                >
                  <div
                    style={{
                      fontFamily: SANS,
                      fontSize: 16,
                      fontWeight: 600,
                      color: C.text,
                      marginBottom: 4,
                    }}
                  >
                    {n.title || "Untitled thought"}
                  </div>
                  <div
                    style={{
                      fontFamily: BODY,
                      fontSize: 13,
                      color: C.textFaint,
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
                  <div style={{ fontFamily: BODY, fontSize: 11, color: C.textFaint }}>
                    {new Date(n.updatedAt).toLocaleDateString("en-US", {
                      month: "short",
                      day: "numeric",
                      year: "numeric",
                    })}
                  </div>
                </motion.button>
              );
            })}
          </div>
        )}

        {/* Tip footer */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.45, duration: 0.4 }}
          className="mt-12 rounded-2xl p-5"
          style={{ background: C.surface, border: `1px solid ${C.borderAlt}` }}
        >
          <p
            style={{
              fontFamily: BODY,
              fontSize: 11,
              color: C.textFaint,
              letterSpacing: "0.1em",
              textTransform: "uppercase",
              marginBottom: 8,
            }}
          >
            Tip
          </p>
          <p style={{ fontFamily: BODY, fontSize: 14, color: C.text, lineHeight: 1.55 }}>
            Highlight any math expression — like <strong style={{ color: C.accent }}>4*4+1</strong>,{" "}
            <strong style={{ color: C.accent }}>f(x) = x² + 1</strong>, or{" "}
            <strong style={{ color: C.accent }}>average rate of change of x² on [2, 5]</strong> —
            and a <em>Visualize</em> pill appears in the selection toolbar.
          </p>
        </motion.div>
      </motion.div>
    </div>
  );
};

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
    <div className="flex h-full" style={{ background: C.bg }}>
      {/* Notes list */}
      <div
        className="flex flex-col"
        style={{ width: 340, borderRight: `1px solid ${C.border}`, background: C.bg }}
      >
        <div className="px-6 pt-8 pb-4">
          <h2 style={{ fontFamily: SANS, fontSize: 32, fontWeight: 600, color: C.text, marginBottom: 16 }}>
            All notes
          </h2>
          <div className="relative">
            <Search
              size={14}
              strokeWidth={1.5}
              className="absolute left-4 top-1/2 -translate-y-1/2"
              style={{ color: C.textFaint }}
            />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search notes..."
              className="w-full pl-10 pr-4 py-2.5 rounded-full outline-none transition-colors"
              style={{
                background: C.surface,
                border: `1px solid ${C.borderAlt}`,
                fontFamily: BODY,
                fontSize: 14,
                color: C.text,
              }}
              onFocus={(e) => (e.currentTarget.style.borderColor = C.accent)}
              onBlur={(e) => (e.currentTarget.style.borderColor = C.borderAlt)}
            />
          </div>
        </div>

        <div className="flex-1 overflow-auto px-4 pb-6">
          <AnimatePresence mode="wait">
            {filtered.length === 0 ? (
              <motion.div
                key="empty"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.25 }}
                className="px-2 py-8 text-center"
              >
                <p style={{ fontFamily: BODY, fontStyle: "italic", fontSize: 18, color: C.textFaint, marginBottom: 8 }}>
                  Your first thought belongs here.
                </p>
                <motion.button
                  onClick={onNew}
                  whileHover={{ scale: 1.03 }}
                  whileTap={{ scale: 0.97 }}
                  className="mt-4 px-4 py-2 rounded-full"
                  style={{
                    background: C.accent,
                    color: C.accentText,
                    fontFamily: BODY,
                    fontSize: 13,
                    fontWeight: 500,
                  }}
                >
                  Create note
                </motion.button>
              </motion.div>
            ) : (
              <motion.div key="list" layout>
                {filtered.map((n, idx) => {
                  const active = n.id === selectedId;
                  const preview = n.contentHtml.replace(/<[^>]+>/g, " ").slice(0, 90);
                  return (
                    <motion.button
                      key={n.id}
                      layout
                      initial={{ opacity: 0, y: 4 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.25, delay: Math.min(idx, 6) * 0.025, ease: EASE }}
                      whileHover={{ y: -1 }}
                      whileTap={{ scale: 0.99 }}
                      onClick={() => setSelectedId(n.id)}
                      className="w-full text-left p-4 mb-2 rounded-2xl"
                      style={{
                        background: C.surface,
                        border: `1px solid ${active ? C.accent : C.borderAlt}`,
                      }}
                    >
                      <div style={{ fontFamily: SANS, fontSize: 18, fontWeight: 600, color: C.text, marginBottom: 4 }}>
                        {n.title || "Untitled thought"}
                      </div>
                      <div
                        style={{
                          fontFamily: BODY,
                          fontSize: 13,
                          color: C.textFaint,
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
                      <div style={{ fontFamily: BODY, fontSize: 11, color: C.textFaint }}>
                        {new Date(n.updatedAt).toLocaleDateString("en-US", { month: "short", day: "numeric" })}
                        {n.sideNotes.length > 0 && (
                          <span className="ml-2">· {n.sideNotes.length} side note{n.sideNotes.length === 1 ? "" : "s"}</span>
                        )}
                      </div>
                    </motion.button>
                  );
                })}
              </motion.div>
            )}
          </AnimatePresence>
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
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.4 }}
            className="h-full flex items-center justify-center px-12"
          >
            <div className="text-center max-w-md">
              <BotanicalAccent
                className="w-24 h-24 mx-auto mb-6 opacity-40"
                style={{ color: C.accent } as React.CSSProperties}
              />
              <p style={{ fontFamily: BODY, fontStyle: "italic", fontSize: 26, color: C.accent, marginBottom: 12 }}>
                Select a note, or begin a new one.
              </p>
              <p style={{ fontFamily: BODY, fontSize: 14, color: C.textFaint }}>
                Highlight any concept while you write to bring it to life.
              </p>
            </div>
          </motion.div>
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
    matchedExpression: ExpressionHit | null;
  }>({ visible: false, x: 0, y: 0, selectedText: "", matchedTopic: null, matchedExpression: null });
  const [animating, setAnimating] = useState<{
    topic: AnimatableTopic;
    context: string;
    breakdown: BreakdownSection[] | null;
    loading: boolean;
    videoUrl?: string;
    error?: string;
    override?: { scene: string; params: Record<string, unknown> };
  } | null>(null);
  const [sideNoteDraft, setSideNoteDraft] = useState<{ anchor: string; body: string } | null>(null);
  const liveRenderProgress = useLiveProgress(animating?.topic.id ?? null);
  const renderProgress = useEstimatedProgress(animating?.loading === true, 10, liveRenderProgress);

  // Initialize editor content once per note. Decorate after the DOM is in place
  // (and re-decorate whenever the topic catalog arrives/changes).
  useEffect(() => {
    if (editorRef.current && editorRef.current.innerHTML !== note.contentHtml) {
      editorRef.current.innerHTML = note.contentHtml;
    }
    setTitle(note.title);
    if (editorRef.current && topics.length) decorateTopicHints(editorRef.current, topics);
  }, [note.id]);

  useEffect(() => {
    if (editorRef.current && topics.length) {
      const offset = getCaretOffset(editorRef.current);
      decorateTopicHints(editorRef.current, topics);
      if (offset !== null) setCaretOffset(editorRef.current, offset);
    }
  }, [topics]);

  // Debounced re-decorate after typing. 500ms beats both the 400ms persist
  // debounce and a comfortable typing rhythm — it kicks in once you pause.
  const decorateTimer = useRef<number | null>(null);
  const scheduleDecorate = useCallback(() => {
    if (decorateTimer.current !== null) window.clearTimeout(decorateTimer.current);
    decorateTimer.current = window.setTimeout(() => {
      if (!editorRef.current) return;
      const offset = getCaretOffset(editorRef.current);
      decorateTopicHints(editorRef.current, topics);
      if (offset !== null) setCaretOffset(editorRef.current, offset);
    }, 500);
  }, [topics]);
  useEffect(() => () => {
    if (decorateTimer.current !== null) window.clearTimeout(decorateTimer.current);
  }, []);

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
    // Only run expression detection when no topic matched — topic catalog
    // entries are intentionally curated and should win over heuristics.
    const expr = matched ? null : detectExpression(text);
    setToolbar({
      visible: true,
      x: rect.left - editorRect.left + rect.width / 2,
      y: rect.top - editorRect.top - 50,
      selectedText: text,
      matchedTopic: matched,
      matchedExpression: expr,
    });
  }, [topics]);

  useEffect(() => {
    document.addEventListener("selectionchange", handleSelection);
    return () => document.removeEventListener("selectionchange", handleSelection);
  }, [handleSelection]);

  // Save title (debounced)
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
    document.execCommand("hiliteColor", false, C.highlight);
    if (editorRef.current) {
      onUpdate({
        ...note,
        title,
        contentHtml: editorRef.current.innerHTML,
        updatedAt: Date.now(),
      });
    }
  };

  const animate = async (
    topic: AnimatableTopic,
    contextText?: string,
    opts?: { bypassCache?: boolean; sceneOverride?: { scene: string; params: Record<string, unknown> } }
  ) => {
    setToolbar((t) => ({ ...t, visible: false }));
    const ctx = (contextText ?? toolbar.selectedText ?? "").trim();
    setAnimating({ topic, context: ctx, breakdown: null, loading: true, override: opts?.sceneOverride });

    const key = cacheKey(topic.id, ctx);
    if (!opts?.bypassCache) {
      const cached = animCache.get(key);
      if (cached) {
        setAnimating({
          topic,
          context: ctx,
          loading: false,
          breakdown: cached.sections,
          videoUrl: cached.videoUrl,
          error: cached.error,
          override: opts?.sceneOverride,
        });
        return;
      }
    } else {
      animCache.delete(key);
    }

    const [animResult, sections] = await Promise.all([
      generateAnimation(topic, ctx || undefined, opts?.sceneOverride),
      explainProblem(ctx, topic),
    ]);
    const result: CachedAnim = {
      videoUrl: animResult.status === "ready" ? animResult.videoUrl : undefined,
      error:    animResult.status === "error" ? animResult.error : undefined,
      sections,
    };
    animCache.set(key, result);
    setAnimating({
      topic,
      context: ctx,
      loading: false,
      breakdown: sections,
      override: opts?.sceneOverride,
      ...result,
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

  // Click-to-animate on auto-highlighted hints. We use mousedown (caught
  // before the browser starts a text selection) so a single click on the
  // underlined span fires the animation rather than just placing the caret.
  // Holding shift falls through to normal selection behavior.
  const onEditorMouseDown = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.shiftKey) return;
    const target = e.target as HTMLElement | null;
    if (!target) return;

    const topicHint = target.closest("span.topic-hint") as HTMLElement | null;
    if (topicHint?.dataset.topicId) {
      const topic = topics.find((t) => t.id === topicHint.dataset.topicId);
      if (topic) {
        e.preventDefault();
        // Look up to the nearest block-ish parent for context (so a hint on
        // "quick sort" picks up "[1,4,6,...]" written next to it on the same line).
        const block = (topicHint.closest("p, div, h1, h2, h3, li, blockquote") as HTMLElement | null)
          ?? topicHint.parentElement;
        const ctx = block?.textContent || topicHint.textContent || "";
        const override = arrayOverrideFor(topic, ctx);
        animate(topic, ctx, override ? { sceneOverride: override } : undefined);
        return;
      }
    }

    const exprHint = target.closest("span.expr-hint") as HTMLElement | null;
    if (exprHint?.dataset.exprKey) {
      const hit = exprHitCache.get(exprHint.dataset.exprKey);
      if (hit) {
        e.preventDefault();
        const synthetic: AnimatableTopic = {
          id: `expr::${exprKey(hit)}`,
          name: hit.displayName,
          category: "arithmetic",
          keywords: [],
          description: `Auto-detected expression: ${hit.matchedText}`,
        };
        animate(synthetic, hit.matchedText, {
          sceneOverride: { scene: hit.scene, params: hit.params },
        });
      }
    }
  };

  return (
    <div className="flex h-full">
      <div className="flex-1 overflow-auto" style={{ background: C.surface }}>
        <div className="max-w-3xl mx-auto px-16 py-16 relative">
          {/* Title */}
          <div className="mb-2 flex items-center justify-between">
            <span
              style={{
                fontFamily: BODY,
                fontSize: 12,
                color: C.textFaint,
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
            <motion.button
              onClick={onDelete}
              whileHover={{ scale: 1.08 }}
              whileTap={{ scale: 0.92 }}
              className="p-2 rounded-full transition-colors"
              style={{ color: C.textFaint }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = C.surfaceHi;
                e.currentTarget.style.color = C.danger;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = "transparent";
                e.currentTarget.style.color = C.textFaint;
              }}
              title="Delete note"
            >
              <Trash2 size={16} strokeWidth={1.5} />
            </motion.button>
          </div>

          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Untitled thought"
            className="w-full outline-none bg-transparent mb-8"
            style={{
              fontFamily: SANS,
              fontSize: 48,
              fontWeight: 600,
              color: C.text,
              letterSpacing: "-0.02em",
              lineHeight: 1.1,
            }}
          />

          {/* Editor */}
          <div className="relative">
            <AnimatePresence>
              {toolbar.visible && (
                <motion.div
                  key="sel-toolbar"
                  initial={{ opacity: 0, scale: 0.92, y: 4 }}
                  animate={{ opacity: 1, scale: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.96, y: 2 }}
                  transition={{ type: "spring", stiffness: 480, damping: 32 }}
                  className="absolute z-20 flex items-center gap-1 px-2 py-1.5 rounded-full"
                  style={{
                    left: toolbar.x,
                    top: toolbar.y,
                    transform: "translateX(-50%)",
                    background: C.surface,
                    border: `1px solid ${C.border}`,
                    boxShadow: "0 8px 32px rgba(0, 0, 0, 0.5)",
                  }}
                >
                  <ToolbarBtn icon={<Bold size={14} strokeWidth={2} />} onClick={() => exec("bold")} label="Bold" />
                  <ToolbarBtn icon={<Italic size={14} strokeWidth={2} />} onClick={() => exec("italic")} label="Italic" />
                  <ToolbarBtn icon={<Highlighter size={14} strokeWidth={1.8} />} onClick={applyHighlight} label="Highlight" />
                  <div style={{ width: 1, height: 16, background: C.borderAlt, margin: "0 2px" }} />
                  <ToolbarBtn icon={<StickyNote size={14} strokeWidth={1.8} />} onClick={startSideNote} label="Side note" />
                  {toolbar.matchedTopic && (
                    <motion.button
                      whileHover={{ scale: 1.04 }}
                      whileTap={{ scale: 0.96 }}
                      onClick={() => {
                        const topic = toolbar.matchedTopic!;
                        const override = arrayOverrideFor(topic, toolbar.selectedText);
                        animate(topic, toolbar.selectedText, override ? { sceneOverride: override } : undefined);
                      }}
                      className="ml-1 px-3 py-1 rounded-full flex items-center gap-1.5"
                      style={{
                        background: C.accent,
                        color: C.accentText,
                        fontFamily: BODY,
                        fontSize: 12,
                        fontWeight: 500,
                      }}
                    >
                      <Sparkles size={12} strokeWidth={2} />
                      Animate "{toolbar.matchedTopic.name}"
                    </motion.button>
                  )}
                  {!toolbar.matchedTopic && toolbar.matchedExpression && (
                    <motion.button
                      whileHover={{ scale: 1.04 }}
                      whileTap={{ scale: 0.96 }}
                      onClick={() => {
                        const e = toolbar.matchedExpression!;
                        const synthetic: AnimatableTopic = {
                          id: `expr::${exprKey(e)}`,
                          name: e.displayName,
                          category: "arithmetic",
                          keywords: [],
                          description: `Auto-detected expression: ${e.matchedText}`,
                        };
                        animate(synthetic, e.matchedText, {
                          sceneOverride: { scene: e.scene, params: e.params },
                        });
                      }}
                      className="ml-1 px-3 py-1 rounded-full flex items-center gap-1.5"
                      style={{
                        background: C.accent,
                        color: C.accentText,
                        fontFamily: BODY,
                        fontSize: 12,
                        fontWeight: 500,
                      }}
                    >
                      <Sparkles size={12} strokeWidth={2} />
                      Visualize {toolbar.matchedExpression.displayName}
                    </motion.button>
                  )}
                  {!toolbar.matchedTopic && !toolbar.matchedExpression && isLikelyMath(toolbar.selectedText) && (
                    <motion.button
                      whileHover={{ scale: 1.04 }}
                      whileTap={{ scale: 0.96 }}
                      onClick={() => {
                        const text = toolbar.selectedText;
                        const snippet = text.length > 40 ? text.slice(0, 40) + "…" : text;
                        const synthetic: AnimatableTopic = {
                          id: `llm::${text.slice(0, 120)}`,
                          name: snippet,
                          category: "calculus",
                          keywords: [],
                          description: text,
                        };
                        // No sceneOverride → falls through to /ask (LLM planner).
                        animate(synthetic, text);
                      }}
                      className="ml-1 px-3 py-1 rounded-full flex items-center gap-1.5"
                      style={{
                        background: "transparent",
                        border: `1px solid ${C.accent}`,
                        color: C.accent,
                        fontFamily: BODY,
                        fontSize: 12,
                        fontWeight: 500,
                      }}
                      title="Send to the LLM planner — slower, may not always succeed"
                    >
                      <Sparkles size={12} strokeWidth={2} />
                      Visualize this
                    </motion.button>
                  )}
                </motion.div>
              )}
            </AnimatePresence>

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
                  scheduleDecorate();
                }
              }}
              onMouseDown={onEditorMouseDown}
              className="outline-none min-h-[300px] note-content"
              style={{
                fontFamily: BODY,
                fontSize: 17,
                color: C.text,
                lineHeight: 1.7,
              }}
              data-placeholder="Start writing, paste a transcript, or import something beautiful..."
            />
            <style>{`
              [contenteditable]:empty::before {
                content: attr(data-placeholder);
                color: #6A6A6A;
                font-family: 'Inter', sans-serif;
                font-size: 17px;
                pointer-events: none;
              }
              .topic-hint {
                border-bottom: 1px dashed ${C.accent};
                cursor: pointer;
                border-radius: 2px;
                padding: 0 1px;
                transition: background 150ms ease;
              }
              .topic-hint:hover {
                background: rgba(37, 99, 235, 0.16);
              }
              .expr-hint {
                border-bottom: 1px dotted ${C.warning};
                background: rgba(245, 212, 92, 0.10);
                cursor: pointer;
                border-radius: 2px;
                padding: 0 2px;
                font-variant-numeric: tabular-nums;
                transition: background 150ms ease;
              }
              .expr-hint:hover {
                background: rgba(245, 212, 92, 0.26);
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
                transition={{ duration: 0.4, ease: EASE }}
                className="mt-12 rounded-3xl overflow-hidden relative"
                style={{
                  border: `1px solid ${C.border}`,
                  background: C.surface,
                }}
              >
                <div
                  className="flex items-center justify-between px-6 py-4 border-b"
                  style={{ borderColor: C.borderSoft }}
                >
                  <div className="flex items-center gap-2">
                    <Sparkles size={14} strokeWidth={1.5} style={{ color: C.accent }} />
                    <span style={{ fontFamily: BODY, fontStyle: "italic", fontSize: 18, color: C.accent }}>
                      {animating.topic.name}
                    </span>
                  </div>
                  <div className="flex items-center gap-1">
                    {!animating.loading && (
                      <motion.button
                        onClick={() => animate(animating.topic, animating.context, { bypassCache: true, sceneOverride: animating.override })}
                        whileHover={{ scale: 1.04 }}
                        whileTap={{ scale: 0.96 }}
                        className="px-3 py-1 rounded-full"
                        style={{
                          background: "transparent",
                          border: `1px solid ${animating.error ? C.danger : C.borderAlt}`,
                          color: animating.error ? C.danger : C.textMuted,
                          fontFamily: BODY,
                          fontSize: 12,
                        }}
                        title="Discard cached result and re-render"
                      >
                        ↻ Re-render
                      </motion.button>
                    )}
                    <motion.button
                      onClick={() => setAnimating(null)}
                      whileHover={{ scale: 1.1, background: C.surfaceHi }}
                      whileTap={{ scale: 0.92 }}
                      className="p-1.5 rounded-full"
                      style={{ color: C.textFaint }}
                    >
                      <X size={14} strokeWidth={1.5} />
                    </motion.button>
                  </div>
                </div>

                {/* Animation surface */}
                <div
                  className="aspect-video flex items-center justify-center relative"
                  style={{ background: C.bg }}
                >
                  <AnimatePresence mode="wait">
                    {animating.loading ? (
                      <motion.div
                        key="loader"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        transition={{ duration: 0.25 }}
                        className="flex flex-col items-center gap-3"
                      >
                        <p style={{ fontFamily: BODY, fontStyle: "italic", fontSize: 16, color: C.textFaint, marginBottom: 8 }}>
                          Rendering your animation...
                        </p>
                        <ProgressBar width={260} progress={renderProgress} />
                      </motion.div>
                    ) : animating.videoUrl ? (
                      <motion.video
                        key="video"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ duration: 0.35 }}
                        src={animating.videoUrl}
                        autoPlay
                        controls
                        className="w-full h-full object-contain"
                        style={{ background: "#0d1117" }}
                      />
                    ) : (
                      <motion.div
                        key="placeholder"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        transition={{ duration: 0.3 }}
                        className="flex flex-col items-center gap-2 w-full h-full"
                      >
                        <ManimPlaceholder topic={animating.topic} />
                        {animating.error && (
                          <p
                            style={{
                              fontSize: 12,
                              color: C.danger,
                              fontFamily: BODY,
                              padding: "0 16px 12px",
                              textAlign: "center",
                            }}
                          >
                            {animating.error}
                          </p>
                        )}
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>

                {/* Breakdown */}
                {animating.breakdown && (
                  <div className="px-8 py-6">
                    <p
                      style={{
                        fontFamily: BODY,
                        fontSize: 11,
                        color: C.textFaint,
                        letterSpacing: "0.1em",
                        textTransform: "uppercase",
                        marginBottom: 16,
                      }}
                    >
                      Problem breakdown
                    </p>
                    {animating.breakdown.map((s, i) => (
                      <motion.div
                        key={i}
                        initial={{ opacity: 0, y: 6 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: i * 0.07, duration: 0.32, ease: EASE }}
                        className="mb-4 flex gap-4"
                      >
                        <div
                          style={{
                            fontFamily: BODY,
                            fontStyle: "italic",
                            fontSize: 16,
                            color: C.accent,
                            minWidth: 120,
                          }}
                        >
                          {s.label}
                        </div>
                        <div
                          style={{
                            fontFamily: BODY,
                            fontSize: 14,
                            color: C.text,
                            lineHeight: 1.6,
                            flex: 1,
                          }}
                        >
                          {s.body}
                        </div>
                      </motion.div>
                    ))}
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* Side notes column */}
      <AnimatePresence>
        {(note.sideNotes.length > 0 || sideNoteDraft) && (
          <motion.div
            key="side-col"
            initial={{ width: 0, opacity: 0 }}
            animate={{ width: 280, opacity: 1 }}
            exit={{ width: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: EASE }}
            className="overflow-hidden"
            style={{ borderLeft: `1px solid ${C.border}`, background: C.bg }}
          >
            <div style={{ width: 280 }} className="overflow-auto h-full">
              <div className="px-5 pt-8 pb-4">
                <p style={{ fontFamily: BODY, fontStyle: "italic", fontSize: 16, color: C.accent, marginBottom: 16 }}>
                  Side notes
                </p>
              </div>
              <div className="px-4 pb-6 space-y-3">
                <AnimatePresence initial={false}>
                  {note.sideNotes.map((s) => (
                    <motion.div
                      key={s.id}
                      layout
                      initial={{ opacity: 0, x: 20, scale: 0.96 }}
                      animate={{ opacity: 1, x: 0, scale: 1 }}
                      exit={{ opacity: 0, x: 20, scale: 0.96 }}
                      transition={{ duration: 0.28, ease: EASE }}
                      className="p-4 rounded-2xl group relative"
                      style={{ background: C.surface, border: `1px solid ${C.border}` }}
                    >
                      <button
                        onClick={() => deleteSideNote(s.id)}
                        className="absolute top-2 right-2 p-1 rounded opacity-0 group-hover:opacity-100 transition-opacity"
                        style={{ color: C.textFaint }}
                      >
                        <X size={12} strokeWidth={1.5} />
                      </button>
                      <div
                        style={{
                          fontFamily: BODY,
                          fontSize: 11,
                          color: C.textFaint,
                          fontStyle: "italic",
                          marginBottom: 6,
                          paddingLeft: 8,
                          borderLeft: `2px solid ${C.warning}`,
                        }}
                      >
                        "{s.anchor.length > 60 ? s.anchor.slice(0, 60) + "…" : s.anchor}"
                      </div>
                      <div style={{ fontFamily: BODY, fontSize: 13, color: C.text, lineHeight: 1.55 }}>
                        {s.body}
                      </div>
                    </motion.div>
                  ))}

                  {sideNoteDraft && (
                    <motion.div
                      key="draft"
                      layout
                      initial={{ opacity: 0, x: 20, scale: 0.96 }}
                      animate={{ opacity: 1, x: 0, scale: 1 }}
                      exit={{ opacity: 0, x: 20, scale: 0.96 }}
                      transition={{ duration: 0.28, ease: EASE }}
                      className="p-4 rounded-2xl"
                      style={{ background: C.surface, border: `1px solid ${C.warning}` }}
                    >
                      <div
                        style={{
                          fontFamily: BODY,
                          fontSize: 11,
                          color: C.textFaint,
                          fontStyle: "italic",
                          marginBottom: 8,
                          paddingLeft: 8,
                          borderLeft: `2px solid ${C.warning}`,
                        }}
                      >
                        "{sideNoteDraft.anchor.length > 60 ? sideNoteDraft.anchor.slice(0, 60) + "…" : sideNoteDraft.anchor}"
                      </div>
                      <textarea
                        autoFocus
                        value={sideNoteDraft.body}
                        onChange={(e) => setSideNoteDraft({ ...sideNoteDraft, body: e.target.value })}
                        placeholder="Add your thought..."
                        className="w-full outline-none resize-none bg-transparent"
                        rows={3}
                        style={{ fontFamily: BODY, fontSize: 13, color: C.text, lineHeight: 1.55 }}
                      />
                      <div className="flex gap-2 mt-2">
                        <motion.button
                          onClick={saveSideNote}
                          whileHover={{ scale: 1.04 }}
                          whileTap={{ scale: 0.96 }}
                          className="px-3 py-1 rounded-full"
                          style={{
                            background: C.accent,
                            color: C.accentText,
                            fontFamily: BODY,
                            fontSize: 12,
                            fontWeight: 500,
                          }}
                        >
                          Save
                        </motion.button>
                        <button
                          onClick={() => setSideNoteDraft(null)}
                          className="px-3 py-1 rounded-full"
                          style={{
                            background: "transparent",
                            color: C.textFaint,
                            fontFamily: BODY,
                            fontSize: 12,
                          }}
                        >
                          Cancel
                        </button>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

const ToolbarBtn: React.FC<{ icon: React.ReactNode; onClick: () => void; label: string }> = ({
  icon,
  onClick,
  label,
}) => (
  <motion.button
    onClick={onClick}
    title={label}
    whileHover={{ scale: 1.1, background: C.surfaceHi }}
    whileTap={{ scale: 0.9 }}
    transition={{ duration: 0.12 }}
    className="p-2 rounded-full"
    style={{ color: C.textMuted, background: "transparent" }}
  >
    {icon}
  </motion.button>
);

// Progress estimator. If a real backend-reported progress is provided, use
// it (smoothed against the asymptotic estimate so it never goes backward).
// Otherwise fall back to `1 - exp(-elapsed / tau)`. Tau is the time at which
// the bar reaches ~63%; tune to match expected render duration.
function useEstimatedProgress(active: boolean, tau = 8, realProgress?: number | null): number {
  const [estimated, setEstimated] = useState(0);
  useEffect(() => {
    if (!active) { setEstimated(0); return; }
    const start = Date.now();
    const id = window.setInterval(() => {
      const elapsed = (Date.now() - start) / 1000;
      setEstimated(1 - Math.exp(-elapsed / tau));
    }, 150);
    return () => window.clearInterval(id);
  }, [active, tau]);
  if (typeof realProgress === "number" && realProgress > 0) {
    // Show whichever is higher so the bar never visually regresses when
    // backend progress lags the time-based estimate.
    return Math.max(realProgress, estimated);
  }
  return estimated;
}

// Progress bar. Pass `progress` (0-1) for a determinate fill with a percent
// label; omit it for an indeterminate sliding chunk (honest "no idea how
// long this will take" mode).
const ProgressBar: React.FC<{ width?: number | string; progress?: number; showPercent?: boolean }> = ({
  width = 220,
  progress,
  showPercent = true,
}) => {
  const track = (
    <div
      className="overflow-hidden rounded-full"
      style={{ width, height: 4, background: "rgba(37, 99, 235, 0.18)" }}
    >
      {progress !== undefined ? (
        <motion.div
          className="h-full rounded-full"
          style={{ background: C.accent }}
          initial={{ width: 0 }}
          animate={{ width: `${Math.max(0, Math.min(1, progress)) * 100}%` }}
          transition={{ duration: 0.35, ease: "easeOut" }}
        />
      ) : (
        <motion.div
          className="h-full rounded-full"
          style={{ width: "35%", background: C.accent }}
          initial={{ x: "-100%" }}
          animate={{ x: ["-100%", "285%"] }}
          transition={{ duration: 1.4, repeat: Infinity, ease: "easeInOut" }}
        />
      )}
    </div>
  );

  if (progress === undefined || !showPercent) {
    return <div className="flex justify-center">{track}</div>;
  }

  return (
    <div className="flex flex-col items-center">
      {track}
      <div
        style={{
          fontFamily: BODY,
          fontSize: 11,
          color: C.textFaint,
          marginTop: 6,
          textAlign: "center",
          fontVariantNumeric: "tabular-nums",
        }}
      >
        {Math.round(Math.max(0, Math.min(1, progress)) * 100)}%
      </div>
    </div>
  );
};

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
            fill={C.accent}
            initial={{ y: 180, height: 0 }}
            animate={{ y: 180 - v * 16, height: v * 16 }}
            transition={{ duration: 0.6, delay: i * 0.1, ease: EASE }}
            rx={2}
          />
        ))}
        <motion.text
          x={200}
          y={30}
          textAnchor="middle"
          fontFamily={SANS}
          fontStyle="italic"
          fontSize="16"
          fill={C.textFaint}
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
            stroke={C.accent}
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
          stroke={C.accent}
          strokeWidth={1.5}
          strokeDasharray="4 4"
          initial={{ pathLength: 0 }}
          animate={{ pathLength: 1 }}
          transition={{ duration: 1 }}
        />
      </svg>
    );
  }
  return (
    <div className="flex flex-col items-center gap-3">
      <motion.div
        animate={{ scale: [1, 1.08, 1], rotate: [0, 8, -8, 0] }}
        transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
      >
        <Sparkles size={32} strokeWidth={1.2} style={{ color: C.accent }} />
      </motion.div>
      <p style={{ fontFamily: BODY, fontStyle: "italic", fontSize: 18, color: C.accent }}>
        {topic.name} animation
      </p>
      <p style={{ fontFamily: BODY, fontSize: 12, color: C.textFaint }}>
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
  const [preview, setPreview] = useState<{
    loading: boolean;
    videoUrl?: string;
    error?: string;
  } | null>(null);
  const liveGalleryProgress = useLiveProgress(selected?.id ?? null);
  const galleryProgress = useEstimatedProgress(preview?.loading === true, 10, liveGalleryProgress);

  // Whenever a topic is selected, check the shared module-level animCache
  // first — if we've rendered this one *successfully* in the current session
  // (here or via the editor's Animate flow), play it back instantly with
  // zero network roundtrips. Failures aren't cached at the gallery level so
  // closing+reopening the modal naturally retries (the editor caches both
  // because clicks there are intentional and we want to avoid duplicate
  // jobs; the gallery is more exploratory).
  const renderTopic = useCallback((topic: AnimatableTopic, force: boolean) => {
    const key = cacheKey(topic.id, "");
    if (!force) {
      const cached = animCache.get(key);
      if (cached?.videoUrl) {
        setPreview({ loading: false, videoUrl: cached.videoUrl });
        return () => {};
      }
    } else {
      animCache.delete(key);
    }
    let cancelled = false;
    setPreview({ loading: true });
    generateAnimation(topic).then((res) => {
      if (cancelled) return;
      const videoUrl = res.status === "ready" ? res.videoUrl : undefined;
      const error    = res.status === "error" ? res.error    : undefined;
      // Only cache successes — let failures retry on the next click.
      if (videoUrl) animCache.set(key, { videoUrl, sections: [] });
      setPreview({ loading: false, videoUrl, error });
    });
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (!selected) {
      setPreview(null);
      return;
    }
    return renderTopic(selected, false);
  }, [selected, renderTopic]);

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
    <div className="h-full overflow-auto" style={{ background: C.bg }}>
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: EASE }}
        className="max-w-5xl mx-auto px-12 py-16"
      >
        <h1
          style={{
            fontFamily: SANS,
            fontSize: 32,
            fontWeight: 600,
            color: C.text,
            lineHeight: 1.2,
            letterSpacing: "-0.02em",
            marginBottom: 40,
          }}
        >
          Concepts we can <em style={{ fontStyle: "normal", color: C.text }}>show you.</em>
        </h1>

        {Object.entries(grouped).map(([cat, list], catIdx) => (
          <motion.div
            key={cat}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: catIdx * 0.06, duration: 0.4, ease: EASE }}
            className="mb-12"
          >
            <h2
              style={{
                fontFamily: BODY,
                fontSize: 12,
                color: C.textFaint,
                letterSpacing: "0.1em",
                textTransform: "uppercase",
                marginBottom: 16,
              }}
            >
              {categoryLabels[cat as AnimatableTopic["category"]]}
            </h2>
            <div className="grid grid-cols-2 gap-4">
              {list.map((t, i) => (
                <motion.button
                  key={t.id}
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: catIdx * 0.06 + i * 0.04, duration: 0.32, ease: EASE }}
                  whileHover={{ y: -3, borderColor: C.accent }}
                  whileTap={{ scale: 0.985 }}
                  onClick={() => setSelected(t)}
                  className="text-left p-6 rounded-3xl relative group"
                  style={{
                    background: C.surface,
                    border: `1px solid ${C.borderAlt}`,
                  }}
                >
                  <Sparkle
                    className="absolute top-4 right-4 w-2.5 h-2.5 opacity-0 group-hover:opacity-100 transition-opacity"
                    style={{ color: C.accent }}
                  />
                  <h3 style={{ fontFamily: SANS, fontSize: 24, fontWeight: 600, color: C.text, marginBottom: 6 }}>
                    {t.name}
                  </h3>
                  <p style={{ fontFamily: BODY, fontSize: 14, color: C.textMuted, lineHeight: 1.5 }}>
                    {t.description}
                  </p>
                </motion.button>
              ))}
            </div>
          </motion.div>
        ))}
      </motion.div>

      <AnimatePresence>
        {selected && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-8"
            style={{ background: "rgba(0, 0, 0, 0.6)" }}
            onClick={() => setSelected(null)}
          >
            <motion.div
              initial={{ scale: 0.96, opacity: 0, y: 8 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              exit={{ scale: 0.96, opacity: 0, y: 8 }}
              transition={{ duration: 0.3, ease: EASE }}
              className="rounded-3xl overflow-hidden max-w-2xl w-full"
              style={{ background: C.surface, boxShadow: "0 8px 32px rgba(0, 0, 0, 0.5)" }}
              onClick={(e) => e.stopPropagation()}
            >
              <div
                className="aspect-video flex items-center justify-center"
                style={{ background: C.bg }}
              >
                <AnimatePresence mode="wait">
                  {preview?.loading ? (
                    <motion.div
                      key="loader"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      transition={{ duration: 0.25 }}
                      className="flex flex-col items-center gap-3 px-6"
                    >
                      <p style={{ fontFamily: BODY, fontStyle: "italic", fontSize: 16, color: C.textFaint, marginBottom: 4 }}>
                        Rendering {selected.name}...
                      </p>
                      <ProgressBar width={260} progress={galleryProgress} />
                    </motion.div>
                  ) : preview?.videoUrl ? (
                    <motion.video
                      key="video"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ duration: 0.35 }}
                      src={preview.videoUrl}
                      autoPlay
                      controls
                      className="w-full h-full object-contain"
                      style={{ background: "#0d1117" }}
                    />
                  ) : (
                    <motion.div
                      key="fallback"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ duration: 0.3 }}
                      className="flex flex-col items-center gap-2 w-full h-full"
                    >
                      <ManimPlaceholder topic={selected} />
                      {preview?.error && (
                        <p
                          style={{
                            fontSize: 12,
                            color: C.danger,
                            fontFamily: BODY,
                            padding: "0 16px 12px",
                            textAlign: "center",
                          }}
                        >
                          {preview.error}
                        </p>
                      )}
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
              <div className="p-8">
                <div className="flex items-start justify-between gap-4 mb-2">
                  <h3 style={{ fontFamily: SANS, fontSize: 32, fontWeight: 600, color: C.text }}>
                    {selected.name}
                  </h3>
                  {!preview?.loading && (
                    <motion.button
                      onClick={() => renderTopic(selected, true)}
                      whileHover={{ scale: 1.04 }}
                      whileTap={{ scale: 0.96 }}
                      className="px-3 py-1 rounded-full mt-2 shrink-0"
                      style={{
                        background: "transparent",
                        border: `1px solid ${preview?.error ? C.danger : C.borderAlt}`,
                        color: preview?.error ? C.danger : C.textMuted,
                        fontFamily: BODY,
                        fontSize: 12,
                      }}
                      title="Discard cached result and re-render"
                    >
                      ↻ Re-render
                    </motion.button>
                  )}
                </div>
                <p style={{ fontFamily: BODY, fontSize: 15, color: C.textMuted, lineHeight: 1.6 }}>
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
      const ocr = await ocrFile(file);
      setStatus({ kind: "formatting", filename: file.name });
      const formatted = await formatNoteFromText(ocr.text);
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
  const importProgress = useEstimatedProgress(isLoading, 4);

  return (
    <div className="h-full overflow-auto" style={{ background: C.bg }}>
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: EASE }}
        className="max-w-3xl mx-auto px-12 py-16"
      >
        <h1
          style={{
            fontFamily: SANS,
            fontSize: 32,
            fontWeight: 600,
            color: C.text,
            lineHeight: 1.2,
            letterSpacing: "-0.02em",
            marginBottom: 12,
          }}
        >
          Photos, formatted <em style={{ fontStyle: "normal", color: C.text }}>with focus.</em>
        </h1>
        <p style={{ fontFamily: BODY, fontSize: 17, color: C.textMuted, lineHeight: 1.6, marginBottom: 40 }}>
          Upload a PDF or photo of your notes. Gemini Flash will read them, write a title,
          and structure them into proper sections — ready to edit.
        </p>

        <AnimatePresence mode="wait">
          {status.kind === "idle" && (
            <motion.div
              key="dropzone"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.25 }}
              onDragOver={(e) => {
                e.preventDefault();
                setDragOver(true);
              }}
              onDragLeave={() => setDragOver(false)}
              onDrop={onDrop}
              onClick={() => inputRef.current?.click()}
              className="rounded-3xl p-16 text-center cursor-pointer"
              style={{
                border: `2px dashed ${C.accent}`,
                background: dragOver ? C.surfaceHi : C.surface,
                transform: dragOver ? "scale(1.01)" : "scale(1)",
                boxShadow: dragOver ? `0 0 0 4px rgba(37, 99, 235, 0.18)` : "none",
                transition: "transform 200ms ease, box-shadow 200ms ease, background 180ms ease",
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
              <motion.div
                animate={dragOver ? { y: [-2, 2, -2] } : { y: 0 }}
                transition={{ duration: 1.2, repeat: dragOver ? Infinity : 0, ease: "easeInOut" }}
              >
                <FileImage size={28} strokeWidth={1.2} className="mx-auto mb-4" style={{ color: C.accent }} />
              </motion.div>
              <p style={{ fontFamily: BODY, fontStyle: "italic", fontSize: 22, color: C.accent, marginBottom: 8 }}>
                Drop a file here, or click to browse.
              </p>
              <p style={{ fontFamily: BODY, fontSize: 13, color: C.textFaint }}>
                PDF · PNG · JPG · WEBP
              </p>
            </motion.div>
          )}

          {isLoading && (
            <motion.div
              key="loading"
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.3, ease: EASE }}
              className="rounded-3xl p-16 text-center"
              style={{ background: C.surface, border: `1px solid ${C.border}` }}
            >
              <p style={{ fontFamily: BODY, fontStyle: "italic", fontSize: 20, color: C.accent, marginBottom: 6 }}>
                {status.kind === "ocr" ? `Reading "${status.filename}"...` : "Structuring your note..."}
              </p>
              <p style={{ fontFamily: BODY, fontSize: 12, color: C.textFaint, marginBottom: 16 }}>
                {status.kind === "ocr" ? "Extracting text" : "Gemini Flash is writing the title and sections"}
              </p>
              <div className="mx-auto" style={{ maxWidth: 320 }}>
                <ProgressBar progress={importProgress} />
              </div>
            </motion.div>
          )}

          {status.kind === "success" && (
            <motion.div
              key="success"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.35, ease: EASE }}
              className="rounded-3xl p-10"
              style={{ background: C.surface, border: `1px solid ${C.border}` }}
            >
              <div className="flex items-center gap-2 mb-4">
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ type: "spring", stiffness: 480, damping: 22, delay: 0.1 }}
                  className="w-6 h-6 rounded-full flex items-center justify-center"
                  style={{ background: C.ok }}
                >
                  <Check size={12} strokeWidth={2.5} color="#FFFFFF" />
                </motion.div>
                <span style={{ fontFamily: BODY, fontStyle: "italic", fontSize: 20, color: C.accent }}>
                  Imported beautifully.
                </span>
              </div>

              <p style={{ fontFamily: BODY, fontSize: 11, color: C.textFaint, letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 6 }}>
                Title
              </p>
              <h3 style={{ fontFamily: SANS, fontSize: 28, fontWeight: 600, color: C.text, marginBottom: 16 }}>
                {status.title}
              </h3>

              <p style={{ fontFamily: BODY, fontSize: 11, color: C.textFaint, letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 8 }}>
                Preview
              </p>
              <div
                className="p-5 rounded-2xl mb-6 note-content"
                style={{
                  background: C.surface,
                  border: `1px solid ${C.borderSoft}`,
                  fontFamily: BODY,
                  fontSize: 14,
                  color: C.text,
                  lineHeight: 1.6,
                  maxHeight: 320,
                  overflow: "auto",
                }}
                dangerouslySetInnerHTML={{ __html: status.html }}
              />

              <div className="flex gap-3">
                <motion.button
                  onClick={saveAsNote}
                  whileHover={{ scale: 1.03 }}
                  whileTap={{ scale: 0.97 }}
                  className="px-5 py-2.5 rounded-full"
                  style={{
                    background: C.accent,
                    color: C.accentText,
                    fontFamily: BODY,
                    fontSize: 14,
                    fontWeight: 500,
                  }}
                >
                  Save as note
                </motion.button>
                <motion.button
                  onClick={() => setStatus({ kind: "idle" })}
                  whileHover={{ scale: 1.03 }}
                  whileTap={{ scale: 0.97 }}
                  className="px-5 py-2.5 rounded-full"
                  style={{
                    background: "transparent",
                    border: `1px solid ${C.warning}`,
                    color: C.warning,
                    fontFamily: BODY,
                    fontSize: 14,
                    fontWeight: 500,
                  }}
                >
                  Import another
                </motion.button>
              </div>
            </motion.div>
          )}

          {status.kind === "error" && (
            <ImportError key="error" message={status.message} onRetry={() => setStatus({ kind: "idle" })} />
          )}
        </AnimatePresence>
      </motion.div>
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
    | { kind: "ready"; problem: string; topic: AnimatableTopic; breakdown: BreakdownSection[]; videoUrl?: string; error?: string }
    | { kind: "error"; message: string }
  >({ kind: "idle" });
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = async (file: File) => {
    try {
      setStatus({ kind: "ocr", filename: file.name });
      const ocr = await ocrFile(file);
      setStatus({ kind: "parsing", filename: file.name });
      const parsed = await parseProblem(ocr.text, topics);
      const topic = topics.find((t) => t.id === parsed.topicId) || null;
      if (!topic) {
        setStatus({ kind: "no-match", problem: parsed.problem });
        return;
      }
      setStatus({ kind: "rendering", problem: parsed.problem, topic });
      const [animResult, breakdown] = await Promise.all([
        generateAnimation(topic, parsed.problem),
        explainProblem(parsed.problem, topic),
      ]);
      setStatus({
        kind: "ready",
        problem: parsed.problem,
        topic,
        breakdown,
        videoUrl: animResult.status === "ready" ? animResult.videoUrl : undefined,
        error:    animResult.status === "error" ? animResult.error : undefined,
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

  const isLoading = status.kind === "ocr" || status.kind === "parsing" || status.kind === "rendering";
  // Render is the long part (~10s); OCR + parse are quick Gemini calls (~3-4s).
  const importTau = status.kind === "rendering" ? 10 : 4;
  const importProgress = useEstimatedProgress(isLoading, importTau);

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
    <div className="h-full overflow-auto" style={{ background: C.bg }}>
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: EASE }}
        className="max-w-4xl mx-auto px-12 py-16"
      >
        <h1
          style={{
            fontFamily: SANS,
            fontSize: 32,
            fontWeight: 600,
            color: C.text,
            lineHeight: 1.2,
            letterSpacing: "-0.02em",
            marginBottom: 12,
          }}
        >
          See it <em style={{ fontStyle: "normal", color: C.text }}>move.</em>
        </h1>
        <p style={{ fontFamily: BODY, fontSize: 17, color: C.textMuted, lineHeight: 1.6, marginBottom: 40 }}>
          Upload a textbook problem. We'll read it, identify the technique, animate the solution,
          and label which part of the figure represents what.
        </p>

        <AnimatePresence mode="wait">
          {status.kind === "idle" && (
            <motion.div
              key="dropzone"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.25 }}
              onDragOver={(e) => {
                e.preventDefault();
                setDragOver(true);
              }}
              onDragLeave={() => setDragOver(false)}
              onDrop={onDrop}
              onClick={() => inputRef.current?.click()}
              className="rounded-3xl p-16 text-center cursor-pointer"
              style={{
                border: `2px dashed ${C.accent}`,
                background: dragOver ? C.surfaceHi : C.surface,
                transform: dragOver ? "scale(1.01)" : "scale(1)",
                boxShadow: dragOver ? `0 0 0 4px rgba(37, 99, 235, 0.18)` : "none",
                transition: "transform 200ms ease, box-shadow 200ms ease, background 180ms ease",
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
              <motion.div
                animate={dragOver ? { y: [-2, 2, -2] } : { y: 0 }}
                transition={{ duration: 1.2, repeat: dragOver ? Infinity : 0, ease: "easeInOut" }}
              >
                <Sparkles size={28} strokeWidth={1.2} className="mx-auto mb-4" style={{ color: C.accent }} />
              </motion.div>
              <p style={{ fontFamily: BODY, fontStyle: "italic", fontSize: 22, color: C.accent, marginBottom: 8 }}>
                Drop a problem here, or click to browse.
              </p>
              <p style={{ fontFamily: BODY, fontSize: 13, color: C.textFaint }}>
                PDF · PNG · JPG · WEBP
              </p>
            </motion.div>
          )}

          {isLoading && (
            <motion.div
              key="loading"
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.3, ease: EASE }}
              className="rounded-3xl p-16 text-center"
              style={{ background: C.surface, border: `1px solid ${C.border}` }}
            >
              <p style={{ fontFamily: BODY, fontStyle: "italic", fontSize: 20, color: C.accent, marginBottom: 6 }}>
                {loadingLabel()}
              </p>
              <p style={{ fontFamily: BODY, fontSize: 12, color: C.textFaint, marginBottom: 16 }}>
                {loadingSub()}
              </p>
              <div className="mx-auto" style={{ maxWidth: 320 }}>
                <ProgressBar progress={importProgress} />
              </div>
            </motion.div>
          )}

          {status.kind === "no-match" && (
            <motion.div
              key="no-match"
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.3, ease: EASE }}
              className="rounded-3xl p-10"
              style={{ background: C.surface, border: `1px solid ${C.border}` }}
            >
              <p style={{ fontFamily: BODY, fontStyle: "italic", fontSize: 22, color: C.accent, marginBottom: 12 }}>
                We couldn't match this to an animatable topic yet.
              </p>
              <p style={{ fontFamily: BODY, fontSize: 14, color: C.textMuted, lineHeight: 1.6, marginBottom: 16 }}>
                Here's what we read:
              </p>
              <div
                className="p-4 rounded-2xl mb-6"
                style={{
                  background: C.surface,
                  border: `1px solid ${C.borderSoft}`,
                  fontFamily: BODY,
                  fontSize: 14,
                  color: C.text,
                  lineHeight: 1.6,
                  whiteSpace: "pre-wrap",
                }}
              >
                {status.problem}
              </div>
              <motion.button
                onClick={() => setStatus({ kind: "idle" })}
                whileHover={{ scale: 1.03 }}
                whileTap={{ scale: 0.97 }}
                className="px-5 py-2.5 rounded-full"
                style={{
                  background: C.accent,
                  color: C.accentText,
                  fontFamily: BODY,
                  fontSize: 14,
                  fontWeight: 500,
                }}
              >
                Try another
              </motion.button>
            </motion.div>
          )}

          {status.kind === "ready" && (
            <motion.div
              key="ready"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.4, ease: EASE }}
              className="rounded-3xl overflow-hidden"
              style={{ background: C.surface, border: `1px solid ${C.border}` }}
            >
              <div
                className="px-8 py-5 flex items-center justify-between"
                style={{ borderBottom: `1px solid ${C.borderSoft}` }}
              >
                <div className="flex items-center gap-2">
                  <Sparkles size={14} strokeWidth={1.5} style={{ color: C.accent }} />
                  <span style={{ fontFamily: BODY, fontStyle: "italic", fontSize: 20, color: C.accent }}>
                    {status.topic.name}
                  </span>
                </div>
                <motion.button
                  onClick={() => setStatus({ kind: "idle" })}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  className="px-4 py-1.5 rounded-full"
                  style={{
                    background: "transparent",
                    border: `1px solid ${C.warning}`,
                    color: C.warning,
                    fontFamily: BODY,
                    fontSize: 12,
                  }}
                >
                  Import another
                </motion.button>
              </div>

              <div className="aspect-video flex items-center justify-center" style={{ background: C.bg }}>
                {status.videoUrl ? (
                  <motion.video
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ duration: 0.35 }}
                    src={status.videoUrl}
                    autoPlay
                    controls
                    className="w-full h-full object-contain"
                    style={{ background: "#0d1117" }}
                  />
                ) : (
                  <div className="flex flex-col items-center gap-2 w-full h-full">
                    <ManimPlaceholder topic={status.topic} />
                    {status.error && (
                      <p
                        style={{
                          fontSize: 12,
                          color: C.danger,
                          fontFamily: BODY,
                          padding: "0 16px 12px",
                          textAlign: "center",
                        }}
                      >
                        {status.error}
                      </p>
                    )}
                  </div>
                )}
              </div>

              <div className="px-8 py-6">
                <p style={{ fontFamily: BODY, fontSize: 11, color: C.textFaint, letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 8 }}>
                  The problem
                </p>
                <div
                  className="p-4 rounded-2xl mb-6"
                  style={{
                    background: C.surface,
                    border: `1px solid ${C.borderSoft}`,
                    fontFamily: BODY,
                    fontSize: 14,
                    color: C.text,
                    lineHeight: 1.6,
                    whiteSpace: "pre-wrap",
                  }}
                >
                  {status.problem}
                </div>

                <p style={{ fontFamily: BODY, fontSize: 11, color: C.textFaint, letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 16 }}>
                  Breakdown
                </p>
                {status.breakdown.map((s, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.07, duration: 0.32, ease: EASE }}
                    className="mb-4 flex gap-4"
                  >
                    <div
                      style={{
                        fontFamily: BODY,
                        fontStyle: "italic",
                        fontSize: 16,
                        color: C.accent,
                        minWidth: 130,
                      }}
                    >
                      {s.label}
                    </div>
                    <div
                      style={{
                        fontFamily: BODY,
                        fontSize: 14,
                        color: C.text,
                        lineHeight: 1.6,
                        flex: 1,
                      }}
                    >
                      {s.body}
                    </div>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          )}

          {status.kind === "error" && (
            <ImportError key="error" message={status.message} onRetry={() => setStatus({ kind: "idle" })} />
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  );
};

const ImportError: React.FC<{ message: string; onRetry: () => void }> = ({ message, onRetry }) => (
  <motion.div
    initial={{ opacity: 0, x: -6 }}
    animate={{ opacity: 1, x: [0, -4, 4, -2, 2, 0] }}
    transition={{ duration: 0.5, ease: EASE }}
    className="rounded-3xl p-10"
    style={{ background: C.surface, border: `1px solid ${C.danger}` }}
  >
    <p style={{ fontFamily: BODY, fontStyle: "italic", fontSize: 20, color: C.danger, marginBottom: 8 }}>
      Something went sideways.
    </p>
    <p style={{ fontFamily: BODY, fontSize: 14, color: C.textMuted, marginBottom: 16 }}>
      {message}
    </p>
    <motion.button
      onClick={onRetry}
      whileHover={{ scale: 1.03 }}
      whileTap={{ scale: 0.97 }}
      className="px-5 py-2.5 rounded-full"
      style={{
        background: C.accent,
        color: C.accentText,
        fontFamily: BODY,
        fontSize: 14,
        fontWeight: 500,
      }}
    >
      Try again
    </motion.button>
  </motion.div>
);

// ─────────────────────────────────────────────────────────────
// Root App
// ─────────────────────────────────────────────────────────────

export default function App() {
  const [route, setRoute] = useState<Route>("home");
  const [notes, setNotes] = useState<Note[]>(() => loadNotes());
  const [topics, setTopics] = useState<AnimatableTopic[]>([]);
  const [selectedNoteId, setSelectedNoteId] = useState<string | null>(null);

  // Load topics from Flask (falls back to MOCK_TOPICS on failure)
  useEffect(() => {
    fetchTopics().then(setTopics);
  }, []);

  // Background pre-render warmup. On app boot, render every TOPIC_SCENE_MAP
  // entry SEQUENTIALLY in the background — one at a time, each waiting for
  // the previous to finish polling. Concurrent manim subprocesses overwhelm
  // typical dev machines (each is ~300MB + 100% CPU) and cause spurious
  // timeouts. Backend cache dedupes, so subsequent boots are no-ops.
  useEffect(() => {
    const flaskUrl = flaskBase();
    const ids = Object.keys(TOPIC_SCENE_MAP);
    let cancelled = false;

    (async () => {
      // Tiny initial delay so the first user interaction always wins the
      // race for the manim subprocess slot.
      await new Promise((r) => setTimeout(r, 2000));
      for (const topicId of ids) {
        if (cancelled) return;
        const direct = TOPIC_SCENE_MAP[topicId];
        if (!direct) continue;
        try {
          const res = await fetch(`${flaskUrl}/render`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              scene: direct.scene,
              params: { caption: topicId, ...direct.params },
            }),
          });
          if (!res.ok) continue;
          const { job_id: jobId } = await res.json();
          if (!jobId) continue;
          // Poll quietly until done/error/timeout — don't write to live
          // progress (warmup shouldn't fight a real user-facing render
          // for the same topic).
          const deadline = Date.now() + 200_000;
          while (!cancelled && Date.now() < deadline) {
            await new Promise((r) => setTimeout(r, 1000));
            const sr = await fetch(`${flaskUrl}/status/${jobId}`);
            if (!sr.ok) continue;
            const job = await sr.json();
            if (job.status === "done" || job.status === "error") break;
          }
        } catch {
          /* best effort — warmup is non-essential */
        }
      }
    })();

    return () => { cancelled = true; };
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
    <div className="flex h-screen w-screen" style={{ fontFamily: BODY, background: C.bg }}>
      <Sidebar route={route} onRoute={setRoute} onNewNote={() => createNote()} />

      <main className="flex-1 overflow-hidden">
        <AnimatePresence mode="wait">
          <motion.div
            key={route}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.18, ease: EASE }}
            className="h-full"
          >
            {route === "home" && (
              <HomePage
                notes={notes}
                topicCount={topics.length}
                onRoute={setRoute}
                onNewNote={() => createNote()}
                onOpenNote={(id) => {
                  setSelectedNoteId(id);
                  setRoute("notes");
                }}
              />
            )}
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
          </motion.div>
        </AnimatePresence>
      </main>
    </div>
  );
}
