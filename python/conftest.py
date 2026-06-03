"""
METACOD GLP-1 module — shared pytest fixtures.

Provides:
  - resources       : loaded rule_pack + drug_db bundle (session-scoped, fast)
  - i18n            : loaded locale dictionaries (session-scoped)
  - db_session      : isolated SQLite per test (function-scoped)
  - client          : FastAPI TestClient wired to the isolated DB (function-scoped)

Layout note: in this repository everything lives flat under `python/` (source
modules, the rule_pack / drug_db / i18n JSON, and the tests/ tree). The original
v4 guide assumed three sibling dirs; here _SRC == the python/ directory.
Override the data directory with METACOD_GLP1_DATA_DIR.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest


# ----- Resolve the source dir (flat layout) and put it on the path -----
_HERE = Path(__file__).resolve().parent          # the python/ directory
_SRC = Path(os.environ.get("METACOD_GLP1_DATA_DIR", _HERE))

if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


# ============================================================================
# Resources (session-scoped — load rule_pack and drug_db once)
# ============================================================================

@pytest.fixture(scope="session")
def data_dir() -> Path:
    """Absolute path to the directory holding rule_pack_v1.json, drug_master_v1.json,
    and the i18n_glp1_*.json files."""
    return _SRC


@pytest.fixture(scope="session")
def resources(data_dir: Path):
    """Loaded ResourceBundle with rule_pack + drug_db."""
    from services.resources import resources_cache
    resources_cache.load(
        rule_pack_path=data_dir / "rule_pack_v1.json",
        drug_db_path=data_dir / "drug_master_v1.json",
    )
    return resources_cache.bundle


@pytest.fixture(scope="session")
def i18n(data_dir: Path):
    """Loaded i18n cache (RU + EN + HE)."""
    from services.i18n import i18n_cache
    i18n_cache.load_all(base_dir=data_dir)
    return i18n_cache


# ============================================================================
# Database (function-scoped — fresh SQLite per test for isolation)
# ============================================================================

@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    """Spin up a fresh SQLite file per test and rebind SessionLocal to it.

    This guarantees:
      - no test bleeds state into another
      - audit_log starts empty per test
      - no cleanup needed; tmp_path is auto-removed by pytest
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    import database

    db_path = tmp_path / "test_metacod.db"
    test_url = f"sqlite:///{db_path}"

    engine = create_engine(
        test_url,
        future=True,
        connect_args={"check_same_thread": False},
    )
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)

    # Rebind module-level SessionLocal so routers/glp1.py picks up the test DB
    monkeypatch.setattr(database, "engine", engine)
    monkeypatch.setattr(database, "SessionLocal", TestSessionLocal)

    database.Base.metadata.create_all(bind=engine)

    yield TestSessionLocal


@pytest.fixture
def db_session(isolated_db):
    """A SQLAlchemy session bound to the isolated DB."""
    session = isolated_db()
    try:
        yield session
    finally:
        session.close()


# ============================================================================
# FastAPI TestClient (function-scoped — uses isolated DB + loaded resources)
# ============================================================================

@pytest.fixture
def client(resources, i18n, isolated_db, monkeypatch):
    """FastAPI TestClient with the isolated DB and pre-loaded resources."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    # Re-import routers.glp1 AFTER monkeypatching SessionLocal in isolated_db, so
    # its get_db() closure picks up the test session factory.
    import importlib
    import routers.glp1 as glp1_router_module
    importlib.reload(glp1_router_module)

    app = FastAPI()
    app.include_router(glp1_router_module.router)

    with TestClient(app) as c:
        yield c
