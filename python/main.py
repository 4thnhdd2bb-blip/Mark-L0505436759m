"""
METACOD GLP-1 module — example FastAPI integration.

This file is a REFERENCE for how to wire the glp1 router into your existing
v4 FastAPI application. Adapt the imports and lifespan setup to your project
structure.

Two integration patterns are supported:

  (1) Mount on existing v4 app (recommended — non-invasive):
      from routers.glp1 import router as glp1_router
      v4_app.include_router(glp1_router)

  (2) Stand-alone development server:
      cd python/ && python main.py
      # or: uvicorn main:app --reload --port 8001

Run order:
  - At startup, services.resources.resources_cache.load() must be called so the
    rule_pack and drug_db are in memory before the first request.
  - Similarly, services.i18n.i18n_cache.load_all() must be called for locales.
  - database.init_db() creates tables on first run (dev). For production,
    use Alembic: alembic upgrade head.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from database import init_db
from routers.glp1 import router as glp1_router
from services.i18n import i18n_cache
from services.resources import resources_cache

# Single-file React UI (Part 3b). Served same-origin so it can call /glp1/* with
# no CORS configuration. Lives under python/ui/.
UI_DIR = Path(__file__).parent / "ui"


# ----- Path resolution -----
# In this flat layout the data files (rule_pack_v1.json, drug_master_v1.json,
# i18n_glp1_*.json) live alongside main.py. Override with env var in production.

BASE_DATA_DIR = Path(os.environ.get(
    "METACOD_GLP1_DATA_DIR",
    Path(__file__).parent,
))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan: load resources at startup, run cleanup at shutdown."""
    # Startup
    print(f"[METACOD GLP-1] Loading resources from {BASE_DATA_DIR}")
    resources_cache.load(
        rule_pack_path=BASE_DATA_DIR / "rule_pack_v1.json",
        drug_db_path=BASE_DATA_DIR / "drug_master_v1.json",
    )
    bundle = resources_cache.bundle
    print(f"[METACOD GLP-1] Loaded {bundle.rule_count} rules "
          f"(rule_pack {bundle.rule_pack_version}), "
          f"{bundle.drug_count} drugs (drug_db {bundle.drug_db_version})")

    i18n_cache.load_all(base_dir=BASE_DATA_DIR)
    print(f"[METACOD GLP-1] Loaded locales: {i18n_cache.available_locales()}")

    # Dev convenience — create tables if they don't exist
    if os.environ.get("METACOD_GLP1_INIT_DB", "0") == "1":
        init_db()
        print("[METACOD GLP-1] Database tables initialised")

    yield

    # Shutdown — nothing to do for now
    print("[METACOD GLP-1] Shutting down")


# ----- App definition -----

app = FastAPI(
    title="METACOD GLP-1 Complication Prevention",
    description=(
        "Clinical decision support for patients on GLP-1 agonists with "
        "concurrent oral therapy. Mechanism-first, evidence-graded, "
        "dual-layer (clinical / admin), trilingual (RU / EN / HE)."
    ),
    version="5.0.0-alpha",
    lifespan=lifespan,
)

# CORS — adjust origins for your deployment
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("METACOD_GLP1_CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the GLP-1 router
app.include_router(glp1_router)

# Serve the single-file UI same-origin (no CORS needed): / -> index.html, /ui/* assets.
if UI_DIR.exists():
    app.mount("/ui", StaticFiles(directory=str(UI_DIR), html=True), name="ui")


# ----- Root: serve the UI (falls back to health JSON if the UI is absent) -----

@app.get("/")
def root():
    index = UI_DIR / "index.html"
    if index.exists():
        return FileResponse(str(index), media_type="text/html")
    return healthz()


@app.get("/healthz")
def healthz() -> dict:
    bundle = resources_cache.bundle
    return {
        "service": "METACOD GLP-1 Complication Prevention",
        "version": "5.0.0-alpha",
        "status": "ok" if bundle.loaded else "starting",
        "rule_pack_version": bundle.rule_pack_version if bundle.loaded else None,
        "drug_db_version": bundle.drug_db_version if bundle.loaded else None,
    }


# ----- Direct run for dev -----

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8001")),
        reload=True,
    )
