"""Tests for the OpenAPI 3.1 schema endpoint (Item #21)."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import create_app
from openapi_spec import build_openapi_spec


@pytest.fixture
def client():
    app = create_app(testing=True)
    return app.test_client()


def test_openapi_endpoint_returns_200(client):
    res = client.get("/openapi.json")
    assert res.status_code == 200
    assert res.headers["Content-Type"].startswith("application/json")


def test_openapi_endpoint_is_valid_openapi_31_doc(client):
    res = client.get("/openapi.json")
    spec = res.get_json()
    assert spec["openapi"].startswith("3.1")
    assert "info" in spec and spec["info"]["title"]
    assert "paths" in spec and len(spec["paths"]) > 0


def test_openapi_documents_critical_endpoints(client):
    res = client.get("/openapi.json")
    spec = res.get_json()
    expected = [
        "/health",
        "/ask",
        "/render",
        "/status/{job_id}",
        "/api/direct-lesson",
        "/api/direct-lesson-stream",
        "/api/share",
        "/api/share/{code}",
    ]
    for path in expected:
        assert path in spec["paths"], f"missing endpoint in OpenAPI: {path}"


def test_openapi_components_reference_resolve():
    """Every $ref in the spec must point at a real component."""
    spec = build_openapi_spec()
    schemas = spec["components"]["schemas"]
    responses = spec["components"]["responses"]

    def collect_refs(node, refs):
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "$ref" and isinstance(v, str):
                    refs.append(v)
                else:
                    collect_refs(v, refs)
        elif isinstance(node, list):
            for item in node:
                collect_refs(item, refs)

    refs: list[str] = []
    collect_refs(spec, refs)
    assert refs, "no $refs in spec — that's suspicious"
    for ref in refs:
        if ref.startswith("#/components/schemas/"):
            name = ref.removeprefix("#/components/schemas/")
            assert name in schemas, f"dangling schema ref: {ref}"
        elif ref.startswith("#/components/responses/"):
            name = ref.removeprefix("#/components/responses/")
            assert name in responses, f"dangling response ref: {ref}"


def test_openapi_direct_lesson_documents_target_minutes(client):
    """Item #10 added target_minutes — schema must list it with bounds."""
    res = client.get("/openapi.json")
    spec = res.get_json()
    req = spec["components"]["schemas"]["DirectLessonRequest"]
    tm = req["properties"]["target_minutes"]
    assert tm["type"] == "number"
    assert tm["minimum"] == 0.5
    assert tm["maximum"] == 10.0
