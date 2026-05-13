"""
OpenAPI 3.1 schema for the Lumen backend (Item #21).

Hand-written rather than scraped from decorators so the public contract stays
explicit. To regenerate a typed frontend client, run:

    npx openapi-typescript http://localhost:5000/openapi.json \\
        -o frontend/src/lib/apiSchema.ts

Only the endpoints the frontend actually depends on are described here — admin
+ debug routes are intentionally omitted to keep the surface small.
"""
from __future__ import annotations


def build_openapi_spec() -> dict:
    """Return the full OpenAPI 3.1 document as a JSON-serializable dict."""
    return {
        "openapi": "3.1.0",
        "info": {
            "title": "Lumen API",
            "version": "1.0.0",
            "description": (
                "Backend API for Lumen — AI math + DSA visualization tool. "
                "Renders Manim animations from natural-language questions."
            ),
        },
        "servers": [
            {"url": "http://localhost:5000", "description": "Local dev"},
        ],
        "paths": {
            "/health": {
                "get": {
                    "summary": "Liveness probe",
                    "responses": {
                        "200": {
                            "description": "ok",
                            "content": {"application/json": {
                                "schema": {"$ref": "#/components/schemas/HealthResponse"},
                            }},
                        },
                    },
                },
            },
            "/topics": {
                "get": {
                    "summary": "List supported topics",
                    "responses": {
                        "200": {
                            "description": "topics list",
                            "content": {"application/json": {
                                "schema": {"$ref": "#/components/schemas/TopicsResponse"},
                            }},
                        },
                    },
                },
            },
            "/ask": {
                "post": {
                    "summary": "Classify a natural-language question and render",
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {
                            "schema": {"$ref": "#/components/schemas/AskRequest"},
                        }},
                    },
                    "responses": {
                        "202": {
                            "description": "queued",
                            "content": {"application/json": {
                                "schema": {"$ref": "#/components/schemas/JobAccepted"},
                            }},
                        },
                        "400": {"$ref": "#/components/responses/BadRequest"},
                        "422": {"$ref": "#/components/responses/Unprocessable"},
                    },
                },
            },
            "/render": {
                "post": {
                    "summary": "Render a specific scene by name",
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {
                            "schema": {"$ref": "#/components/schemas/RenderRequest"},
                        }},
                    },
                    "responses": {
                        "202": {
                            "description": "queued",
                            "content": {"application/json": {
                                "schema": {"$ref": "#/components/schemas/JobAccepted"},
                            }},
                        },
                        "400": {"$ref": "#/components/responses/BadRequest"},
                    },
                },
            },
            "/status/{job_id}": {
                "get": {
                    "summary": "Poll a job's status",
                    "parameters": [
                        {"name": "job_id", "in": "path", "required": True,
                         "schema": {"type": "string"}},
                    ],
                    "responses": {
                        "200": {
                            "description": "status snapshot",
                            "content": {"application/json": {
                                "schema": {"$ref": "#/components/schemas/JobStatus"},
                            }},
                        },
                        "404": {"$ref": "#/components/responses/NotFound"},
                    },
                },
            },
            "/api/direct-lesson": {
                "post": {
                    "summary": "Submit a lesson via the Lesson Director agent",
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {
                            "schema": {"$ref": "#/components/schemas/DirectLessonRequest"},
                        }},
                    },
                    "responses": {
                        "202": {
                            "description": "queued",
                            "content": {"application/json": {
                                "schema": {"$ref": "#/components/schemas/JobAccepted"},
                            }},
                        },
                        "400": {"$ref": "#/components/responses/BadRequest"},
                    },
                },
            },
            "/api/direct-lesson-stream": {
                "post": {
                    "summary": "SSE variant of /api/direct-lesson — streams stage transitions",
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {
                            "schema": {"$ref": "#/components/schemas/DirectLessonRequest"},
                        }},
                    },
                    "responses": {
                        "200": {
                            "description": "event stream",
                            "content": {"text/event-stream": {
                                "schema": {"type": "string"},
                            }},
                        },
                        "400": {"$ref": "#/components/responses/BadRequest"},
                    },
                },
            },
            "/api/share": {
                "post": {
                    "summary": "Create a shareable short code for a finished job",
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {
                            "schema": {"$ref": "#/components/schemas/ShareRequest"},
                        }},
                    },
                    "responses": {
                        "200": {
                            "description": "share record",
                            "content": {"application/json": {
                                "schema": {"$ref": "#/components/schemas/ShareRecord"},
                            }},
                        },
                        "400": {"$ref": "#/components/responses/BadRequest"},
                    },
                },
            },
            "/api/share/{code}": {
                "get": {
                    "summary": "Resolve a share code into its lesson metadata",
                    "parameters": [
                        {"name": "code", "in": "path", "required": True,
                         "schema": {"type": "string", "pattern": "^[A-Za-z0-9]+$"}},
                    ],
                    "responses": {
                        "200": {
                            "description": "share record",
                            "content": {"application/json": {
                                "schema": {"$ref": "#/components/schemas/ShareRecord"},
                            }},
                        },
                        "404": {"$ref": "#/components/responses/NotFound"},
                    },
                },
            },
            "/api/pin": {
                "post": {
                    "summary": "Pin a rendered video so cleanup keeps it on disk",
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {
                            "schema": {"$ref": "#/components/schemas/PinRequest"},
                        }},
                    },
                    "responses": {
                        "200": {
                            "description": "pinned",
                            "content": {"application/json": {
                                "schema": {"$ref": "#/components/schemas/PinResponse"},
                            }},
                        },
                    },
                },
            },
        },
        "components": {
            "responses": {
                "BadRequest": {
                    "description": "validation error",
                    "content": {"application/json": {
                        "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                    }},
                },
                "NotFound": {
                    "description": "not found",
                    "content": {"application/json": {
                        "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                    }},
                },
                "Unprocessable": {
                    "description": "agent or classifier failure",
                    "content": {"application/json": {
                        "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                    }},
                },
            },
            "schemas": {
                "HealthResponse": {
                    "type": "object",
                    "required": ["status"],
                    "properties": {
                        "status": {"type": "string", "enum": ["ok"]},
                    },
                },
                "TopicsResponse": {
                    "type": "object",
                    "required": ["topics"],
                    "properties": {
                        "topics": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                },
                "ErrorResponse": {
                    "type": "object",
                    "required": ["error"],
                    "properties": {
                        "error": {"type": "string"},
                    },
                },
                "AskRequest": {
                    "type": "object",
                    "required": ["question"],
                    "properties": {
                        "question": {"type": "string", "minLength": 1},
                    },
                },
                "RenderRequest": {
                    "type": "object",
                    "required": ["scene", "params"],
                    "properties": {
                        "scene": {"type": "string"},
                        "params": {"type": "object", "additionalProperties": True},
                    },
                },
                "DirectLessonRequest": {
                    "type": "object",
                    "required": ["question"],
                    "properties": {
                        "question": {"type": "string", "minLength": 1},
                        "style": {
                            "type": "string",
                            "enum": ["intuition_first", "rigor_first",
                                     "socratic", "speedrun"],
                        },
                        "target_minutes": {
                            "type": "number",
                            "minimum": 0.5,
                            "maximum": 10.0,
                            "default": 1.5,
                        },
                    },
                },
                "JobAccepted": {
                    "type": "object",
                    "required": ["job_id"],
                    "properties": {
                        "job_id": {"type": "string", "format": "uuid"},
                        "scene": {"type": "string"},
                    },
                },
                "JobStatus": {
                    "type": "object",
                    "required": ["status"],
                    "properties": {
                        "status": {
                            "type": "string",
                            "enum": ["pending", "done", "error"],
                        },
                        "url": {"type": ["string", "null"]},
                        "error": {"type": ["string", "null"]},
                        "stage": {"type": "string"},
                        "progress": {"type": "number"},
                    },
                },
                "ShareRequest": {
                    "type": "object",
                    "required": ["job_id"],
                    "properties": {
                        "job_id": {"type": "string"},
                        "title": {"type": "string"},
                    },
                },
                "ShareRecord": {
                    "type": "object",
                    "required": ["code", "url"],
                    "properties": {
                        "code": {"type": "string"},
                        "url": {"type": "string"},
                        "title": {"type": "string"},
                        "created_at": {"type": "string", "format": "date-time"},
                    },
                },
                "PinRequest": {
                    "type": "object",
                    "required": ["job_id"],
                    "properties": {
                        "job_id": {"type": "string"},
                    },
                },
                "PinResponse": {
                    "type": "object",
                    "required": ["pinned"],
                    "properties": {
                        "pinned": {"type": "boolean"},
                    },
                },
            },
        },
    }
