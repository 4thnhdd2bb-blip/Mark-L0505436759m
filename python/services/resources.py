"""
METACOD GLP-1 module — resource loader and singleton cache.

Loads rule_pack_v1.json and drug_master_v1.json ONCE at application startup
and exposes them through a dependency-injectable accessor.

Designed for FastAPI lifespan event:

    from contextlib import asynccontextmanager
    from services.resources import resources_cache

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        resources_cache.load_from_env()
        yield

Then in routes:

    @router.post("/assess")
    def assess(resources: ResourceBundle = Depends(get_resources)):
        rule_pack = resources.rule_pack
        ...
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ----- Environment variables (overridable per deployment) -----
ENV_RULE_PACK = "METACOD_GLP1_RULE_PACK"
ENV_DRUG_DB = "METACOD_GLP1_DRUG_DB"

DEFAULT_RULE_PACK_NAME = "rule_pack_v2.json"
DEFAULT_DRUG_DB_NAME = "drug_master_v2.json"


@dataclass
class ResourceBundle:
    """Holds the loaded rule_pack and drug_master DB as parsed dicts."""
    rule_pack: dict = field(default_factory=dict)
    drug_db: dict = field(default_factory=dict)
    rule_pack_path: Optional[Path] = None
    drug_db_path: Optional[Path] = None
    loaded: bool = False

    @property
    def rule_pack_version(self) -> str:
        return self.rule_pack.get("rule_pack_version", "unknown")

    @property
    def drug_db_version(self) -> str:
        return self.drug_db.get("schema_version", "unknown")

    @property
    def rule_count(self) -> int:
        return len(self.rule_pack.get("rules", []))

    @property
    def drug_count(self) -> int:
        return len(self.drug_db.get("profiles", []))


class ResourcesCache:
    """Process-level singleton holding the loaded resource bundle."""

    def __init__(self) -> None:
        self._bundle = ResourceBundle()

    @property
    def bundle(self) -> ResourceBundle:
        return self._bundle

    def load(
        self,
        rule_pack_path: str | Path,
        drug_db_path: str | Path,
    ) -> ResourceBundle:
        """Load both resource files from disk."""
        rp_path = Path(rule_pack_path)
        db_path = Path(drug_db_path)

        with open(rp_path, "r", encoding="utf-8") as f:
            rule_pack = json.load(f)
        with open(db_path, "r", encoding="utf-8") as f:
            drug_db = json.load(f)

        self._bundle = ResourceBundle(
            rule_pack=rule_pack,
            drug_db=drug_db,
            rule_pack_path=rp_path,
            drug_db_path=db_path,
            loaded=True,
        )
        return self._bundle

    def load_from_env(self, base_dir: Optional[str | Path] = None) -> ResourceBundle:
        """Resolve paths from env vars; fall back to base_dir + default names."""
        base = Path(base_dir) if base_dir else Path.cwd()

        rp_env = os.environ.get(ENV_RULE_PACK)
        db_env = os.environ.get(ENV_DRUG_DB)

        rp_path = Path(rp_env) if rp_env else base / DEFAULT_RULE_PACK_NAME
        db_path = Path(db_env) if db_env else base / DEFAULT_DRUG_DB_NAME

        return self.load(rp_path, db_path)

    def assert_loaded(self) -> None:
        if not self._bundle.loaded:
            raise RuntimeError(
                "ResourcesCache not initialised. Call load() or load_from_env() "
                "during app startup (FastAPI lifespan event)."
            )


# Module-level singleton
resources_cache = ResourcesCache()


def get_resources() -> ResourceBundle:
    """FastAPI dependency: returns the loaded ResourceBundle.

    Usage:
        @router.post("/assess")
        def assess(resources: ResourceBundle = Depends(get_resources)):
            agent = PharmacistAgent(patient, resources.rule_pack, resources.drug_db)
    """
    resources_cache.assert_loaded()
    return resources_cache.bundle
