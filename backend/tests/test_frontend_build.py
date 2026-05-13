"""
Structural assertions on the frontend production build.

These tests don't run `npm run build` themselves — they assume the dist/
directory exists (CI runs the build separately). They validate that
production assets we depend on are present.
"""
import json
import os
import pytest

_FRONTEND_DIST = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "frontend", "dist",
)


def _dist_exists() -> bool:
    return os.path.isdir(_FRONTEND_DIST)


@pytest.mark.skipif(not _dist_exists(),
                    reason="frontend/dist not present; run npm run build first")
def test_pwa_manifest_emitted_with_required_fields():
    """Item #25 regression: vite-plugin-pwa must produce a valid manifest."""
    manifest_path = os.path.join(_FRONTEND_DIST, "manifest.webmanifest")
    assert os.path.exists(manifest_path), (
        f"PWA manifest missing — vite-plugin-pwa not wired up correctly. "
        f"Expected: {manifest_path}"
    )
    with open(manifest_path, encoding="utf-8") as fh:
        manifest = json.load(fh)
    # The fields a browser actually needs to offer "Add to Home Screen"
    assert manifest.get("name"), "manifest.name missing"
    assert manifest.get("short_name"), "manifest.short_name missing"
    assert manifest.get("start_url"), "manifest.start_url missing"
    assert manifest.get("display") == "standalone", "display must be 'standalone' for installability"
    icons = manifest.get("icons") or []
    assert icons, "manifest must have at least one icon"


@pytest.mark.skipif(not _dist_exists(),
                    reason="frontend/dist not present; run npm run build first")
def test_service_worker_emitted():
    """Item #25 regression: a service worker file must be emitted (sw.js)."""
    sw_candidates = ["sw.js", "service-worker.js"]
    found = [p for p in sw_candidates
             if os.path.exists(os.path.join(_FRONTEND_DIST, p))]
    assert found, f"No service worker emitted; looked for {sw_candidates}"


def test_pwa_plugin_listed_in_package_json():
    """Sanity check the plugin is committed to package.json devDependencies."""
    pkg_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "frontend", "package.json",
    )
    with open(pkg_path, encoding="utf-8") as fh:
        pkg = json.load(fh)
    dev_deps = pkg.get("devDependencies", {})
    assert "vite-plugin-pwa" in dev_deps, "vite-plugin-pwa not in devDependencies"
