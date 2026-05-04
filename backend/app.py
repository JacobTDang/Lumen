import os

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from agent.classifier import classify_domain
from agent.dsa_planner import plan_dsa
from agent.explainer import explain_problem
from agent.planner import plan as plan_math
from renderer.worker import get_job, submit_lesson, submit_render

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
    {"id": "long-division", "name": "Long Division", "category": "arithmetic",
     "keywords": ["long division", "divide"],
     "description": "Step-by-step division algorithm."},
    {"id": "derivative-power-rule", "name": "Power Rule", "category": "calculus",
     "keywords": ["power rule", "derivative of x^n"],
     "description": "Why d/dx[x^n] = n·x^(n-1)."},
    {"id": "torque", "name": "Torque", "category": "physics",
     "keywords": ["torque", "rotational force"],
     "description": "Force × lever arm visualized on a rotating body."},
    {"id": "matrix-multiply", "name": "Matrix Multiplication", "category": "linalg",
     "keywords": ["matrix multiply", "matmul"],
     "description": "Row-by-column dot products animated."},
]


def create_app(testing: bool = False) -> Flask:
    app = Flask(__name__)
    app.config["TESTING"] = testing
    CORS(app)

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
        body     = request.get_json(silent=True) or {}
        question = body.get("question", "").strip()
        if not question:
            return jsonify({"error": "question is required"}), 400
        domain = classify_domain(question)
        try:
            lesson = plan_dsa(question) if domain == "dsa" else plan_math(question)
        except ValueError as e:
            app.logger.warning(f"planner ValueError on q={question[:120]!r}: {e}")
            return jsonify({
                "error": "Could not understand the question. Try rephrasing it.",
            }), 422
        except Exception as e:
            app.logger.exception(f"planner unexpected error on q={question[:120]!r}")
            return jsonify({
                "error": "Internal planning error. Please try again.",
            }), 422
        job_id = submit_lesson(lesson.steps)
        return jsonify({
            "job_id":      job_id,
            "concept":     lesson.concept,
            "domain":      domain,
            "scene_count": len(lesson.steps),
        }), 202

    @app.post("/render")
    def render():
        body   = request.get_json(silent=True) or {}
        scene  = body.get("scene")
        params = body.get("params", {})
        if not scene:
            return jsonify({"error": "scene is required"}), 400
        job_id = submit_render(scene, params)
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
        # Belt-and-suspenders: send_from_directory protects against ".." but we
        # also resolve symlinks and confirm the result is still under media/.
        target = os.path.realpath(os.path.join(media_dir, filename))
        if not target.startswith(media_dir + os.sep):
            return jsonify({"error": "forbidden"}), 403
        return send_from_directory(media_dir, filename)

    return app


if __name__ == "__main__":
    # use_reloader=False is critical: the dev reloader wipes the in-memory
    # _jobs dict mid-render whenever any file is touched, leaving polling
    # frontends stuck on a now-orphaned job_id.
    create_app().run(debug=True, use_reloader=False, port=5000)
