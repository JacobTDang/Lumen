import os

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from agent.classifier import classify_domain
from agent.dsa_planner import plan_dsa
from agent.planner import plan as plan_math
from renderer.worker import get_job, submit_lesson, submit_render


def create_app(testing: bool = False) -> Flask:
    app = Flask(__name__)
    app.config["TESTING"] = testing
    CORS(app)

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

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
            return jsonify({
                "error":  "Could not understand the question. Try rephrasing it.",
                "detail": str(e)[:200],
            }), 422
        except Exception as e:
            return jsonify({
                "error":  "Internal planning error. Please try again.",
                "detail": str(e)[:200],
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
        media_dir = os.path.join(os.path.dirname(__file__), "media")
        return send_from_directory(media_dir, filename)

    return app


if __name__ == "__main__":
    create_app().run(debug=True, port=5000)
