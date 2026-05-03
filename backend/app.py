import json
import os

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from google.genai import types as genai_types

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from agent.classifier import classify_domain
from agent.dsa_planner import plan_dsa
from agent.explainer import explain_problem
from agent.gemini_client import call_gemini
from agent.planner import plan as plan_math
from renderer.worker import get_job, submit_lesson, submit_render
from schemas.types import StepPlan

_TOPICS = [
    {"id": "merge-sort", "name": "Merge Sort", "category": "dsa",
     "keywords": ["merge sort", "mergesort", "divide and conquer sort"],
     "description": "Recursive divide-and-merge visualization with comparison highlights."},
    {"id": "quick-sort", "name": "Quick Sort", "category": "dsa",
     "keywords": ["quick sort", "quicksort", "partition"],
     "description": "Pivot-based partitioning shown step by step."},
    {"id": "binary-search", "name": "Binary Search", "category": "dsa",
     "keywords": ["binary search", "log n search"],
     "description": "Halving the search space on a sorted array."},
    {"id": "chain-rule", "name": "Chain Rule", "category": "calculus",
     "keywords": ["chain rule", "composite derivative", "f(g(x))"],
     "description": "Derivative of nested functions, layer by layer."},
    {"id": "washer-method", "name": "Washer Method", "category": "calculus",
     "keywords": ["washer method", "volume of revolution", "disk method"],
     "description": "Volume of solids of revolution using stacked washers."},
    {"id": "shell-method", "name": "Cylindrical Shell Method", "category": "calculus",
     "keywords": ["cylindrical shell", "shell method", "shells"],
     "description": "Volume by unwrapping concentric cylindrical shells."},
    {"id": "derivative-power-rule", "name": "Power Rule", "category": "calculus",
     "keywords": ["power rule", "derivative of x^n"],
     "description": "Why d/dx[x^n] = n·x^(n-1)."},
]

_MIME_FROM_EXT = {
    "jpg": "image/jpeg", "jpeg": "image/jpeg",
    "png": "image/png", "webp": "image/webp",
    "pdf": "application/pdf",
}
_ALLOWED_MIMES = frozenset(_MIME_FROM_EXT.values())


def create_app(testing: bool = False) -> Flask:
    app = Flask(__name__)
    app.config["TESTING"] = testing
    CORS(app)

    # ── existing endpoints ────────────────────────────────────────

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.get("/topics")
    def topics():
        return jsonify({"topics": _TOPICS})

    @app.post("/breakdown")
    def breakdown():
        body = request.get_json(silent=True) or {}
        topic_name = body.get("topicName", "").strip()
        topic_description = body.get("topicDescription", "").strip()
        problem = body.get("problem", "").strip()
        if not topic_name:
            return jsonify({"error": "topicName is required"}), 400
        sections = explain_problem(problem, topic_name, topic_description)
        return jsonify({"sections": sections})

    @app.post("/ask")
    def ask():
        body = request.get_json(silent=True) or {}
        question = body.get("question", "").strip()
        if not question:
            return jsonify({"error": "question is required"}), 400
        domain = classify_domain(question)
        try:
            lesson = plan_dsa(question) if domain == "dsa" else plan_math(question)
        except ValueError as e:
            app.logger.warning("planner ValueError on q=%r: %s", question[:120], e)
            return jsonify({"error": "Could not understand the question. Try rephrasing it."}), 422
        except Exception:
            app.logger.exception("planner unexpected error on q=%r", question[:120])
            return jsonify({"error": "Internal planning error. Please try again."}), 422
        job_id = submit_lesson(lesson.steps)
        return jsonify({
            "job_id":      job_id,
            "concept":     lesson.concept,
            "domain":      domain,
            "scene_count": len(lesson.steps),
        }), 202

    @app.post("/render")
    def render():
        body = request.get_json(silent=True) or {}
        scene = body.get("scene")
        params = body.get("params", {})
        if not scene:
            return jsonify({"error": "scene is required"}), 400
        # Route through submit_lesson so single-scene renders share the
        # content-hash cache (so /prerender on boot warms /render too).
        step = StepPlan(tool=scene, params=params, caption=params.get("caption", ""))
        job_id = submit_lesson([step])
        return jsonify({"job_id": job_id}), 202

    @app.get("/status/<job_id>")
    def status(job_id):
        job = get_job(job_id)
        if job is None:
            return jsonify({"error": "job not found"}), 404
        return jsonify(job)

    @app.get("/media/<path:filename>")
    def serve_media(filename):
        media_dir = os.path.realpath(os.path.join(os.path.dirname(__file__), "media"))
        target = os.path.realpath(os.path.join(media_dir, filename))
        if not target.startswith(media_dir + os.sep):
            return jsonify({"error": "forbidden"}), 403
        return send_from_directory(media_dir, filename)

    # ── Gemini-backed /api/* endpoints ───────────────────────────

    @app.get("/api/topics")
    def api_topics():
        return jsonify({"topics": _TOPICS})

    @app.post("/api/ocr")
    def api_ocr():
        if "file" not in request.files:
            return jsonify({"error": "No file provided"}), 400
        file = request.files["file"]
        if not file.filename:
            return jsonify({"error": "No file selected"}), 400

        mime_type = file.mimetype or "application/octet-stream"
        if mime_type == "application/octet-stream":
            ext = (file.filename or "").rsplit(".", 1)[-1].lower()
            mime_type = _MIME_FROM_EXT.get(ext, mime_type)
        if mime_type not in _ALLOWED_MIMES:
            return jsonify({"error": f"Unsupported file type: {mime_type}"}), 400

        try:
            file_bytes = file.read()
            prompt = (
                "Extract all text from this image or document exactly as it appears. "
                "Preserve line breaks. Do not summarize, do not add commentary, just transcribe."
            )
            contents = [prompt, genai_types.Part.from_bytes(data=file_bytes, mime_type=mime_type)]
            response = call_gemini(contents)
            return jsonify({"text": response.text})
        except Exception as exc:
            app.logger.exception("OCR failed")
            return jsonify({"error": "OCR failed", "detail": str(exc)}), 500

    @app.post("/api/format-note")
    def api_format_note():
        body = request.get_json(silent=True) or {}
        raw_text = body.get("rawText", "").strip()
        if not raw_text:
            return jsonify({"error": "rawText is required"}), 400

        schema = {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "html":  {"type": "string"},
            },
            "required": ["title", "html"],
        }
        prompt = (
            "You are turning a raw note transcription into a clean, well-structured "
            "study note. Return a JSON object with:\n"
            "- title: a short descriptive title (max 60 characters)\n"
            "- html: well-structured semantic HTML\n\n"
            "HTML rules:\n"
            "- Allowed tags ONLY: <h2>, <h3>, <p>, <ul>, <ol>, <li>, <strong>, <em>\n"
            "- No CSS, no scripts, no inline styles, no class attributes, no <div>/<span>.\n"
            "- Structure with clear visual hierarchy:\n"
            "    * Open with one short overview paragraph (1–2 sentences).\n"
            "    * Use <h2> for major sections (e.g. Definitions, Examples, Steps, Notes).\n"
            "    * Use <h3> for sub-sections inside a major section.\n"
            "    * Keep prose paragraphs short — 2 to 4 sentences max — so the note "
            "      is scannable.\n"
            "- Use <strong> liberally to highlight:\n"
            "    * Key terms on first definition (e.g. <strong>derivative</strong>).\n"
            "    * Names of theorems, methods, formulas, or rules.\n"
            "    * Important numerical values, results, and final answers.\n"
            "    * Anything the reader should remember.\n"
            "- Use <em> sparingly for emphasis or contrast within a sentence.\n"
            "- Use <ul> for unordered lists (properties, characteristics, examples).\n"
            "- Use <ol> for ordered lists (steps, procedures, sequential reasoning).\n"
            "- Wrap each list item in its own <li>; do NOT merge multiple steps into one <li>.\n"
            "- Each section should have its own heading + content; do not pile everything "
            "  into one <h2> block. Aim for 2–5 sections.\n"
            "- Preserve the original meaning; reorganize and clarify, but do not invent "
            "  facts or add content not present in the source.\n\n"
            f"Source text:\n{raw_text}"
        )
        try:
            response = call_gemini(prompt, response_schema=schema)
            return jsonify(json.loads(response.text))
        except Exception as exc:
            app.logger.exception("format-note failed")
            return jsonify({"error": "format-note failed", "detail": str(exc)}), 500

    @app.post("/api/parse-problem")
    def api_parse_problem():
        body = request.get_json(silent=True) or {}
        raw_text = body.get("rawText", "").strip()
        topics_list = body.get("topics", [])
        if not raw_text:
            return jsonify({"error": "rawText is required"}), 400

        schema = {
            "type": "object",
            "properties": {
                "problem": {"type": "string"},
                "topicId": {"type": ["string", "null"]},
            },
            "required": ["problem", "topicId"],
        }
        topics_summary = "\n".join(
            f'- id: {t.get("id")}, name: {t.get("name")}, '
            f'keywords: {", ".join(t.get("keywords", []))}'
            for t in topics_list
        )
        prompt = (
            "Identify which of the available animation topics best matches this student problem. "
            "Return a JSON object with:\n"
            "- problem: cleaned-up problem statement\n"
            "- topicId: the id of the matching topic, or null if none match\n\n"
            f"Problem:\n{raw_text}\n\n"
            f"Available topics:\n{topics_summary or '(none provided)'}"
        )
        try:
            response = call_gemini(prompt, response_schema=schema)
            return jsonify(json.loads(response.text))
        except Exception as exc:
            app.logger.exception("parse-problem failed")
            return jsonify({"error": "parse-problem failed", "detail": str(exc)}), 500

    @app.post("/api/breakdown")
    def api_breakdown():
        body = request.get_json(silent=True) or {}
        problem = body.get("problem", "").strip()
        topic = body.get("topic") or {}
        topic_name = topic.get("name", "").strip()
        topic_description = topic.get("description", "").strip()
        if not topic_name:
            return jsonify({"error": "topic.name is required"}), 400

        schema = {
            "type": "object",
            "properties": {
                "sections": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "label": {"type": "string"},
                            "body":  {"type": "string"},
                        },
                        "required": ["label", "body"],
                    },
                },
            },
            "required": ["sections"],
        }
        prompt = (
            f"Break down this problem step by step in the context of {topic_name}.\n"
            f"Topic: {topic_name} — {topic_description}\n"
            f"Problem: {problem or '(general explanation of the topic)'}\n\n"
            "Return a JSON object with a 'sections' array of 3-5 objects, each with:\n"
            "- label: short title (1-4 words)\n"
            "- body: 1-2 sentence explanation\n\n"
            f"Be specific about what each part represents in the context of {topic_name}."
        )
        try:
            response = call_gemini(prompt, response_schema=schema)
            return jsonify(json.loads(response.text))
        except Exception as exc:
            app.logger.exception("api/breakdown failed")
            return jsonify({"error": "breakdown failed", "detail": str(exc)}), 500

    return app


if __name__ == "__main__":
    # use_reloader=False: the dev reloader wipes the in-memory _jobs dict
    # mid-render whenever any file is touched, orphaning polling frontends.
    create_app().run(debug=True, use_reloader=False, port=5000)
