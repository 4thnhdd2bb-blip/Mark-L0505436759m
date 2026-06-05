"""
Integration test — the single-file UI is served by the FastAPI app same-origin.

Uses TestClient against the real `main.app` (its lifespan loads rule_pack + i18n),
so this also smoke-tests that startup wiring works end to end.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
def test_ui_served_at_root_and_ui_path():
    import main

    with TestClient(main.app) as c:
        # Root serves the HTML shell
        r = c.get("/")
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/html")
        assert "Metacod" in r.text
        assert 'id="root"' in r.text
        assert 'id="ui-i18n"' in r.text  # embedded i18n block present

        # Static asset path also serves it
        r2 = c.get("/ui/index.html")
        assert r2.status_code == 200
        assert r2.headers["content-type"].startswith("text/html")

        # Health probe reports loaded content
        r3 = c.get("/healthz")
        assert r3.status_code == 200
        body = r3.json()
        assert body["status"] == "ok"
        assert body["rule_pack_version"] == "2.0.0"
