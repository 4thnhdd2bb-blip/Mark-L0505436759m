"""
METACOD GLP-1 module — i18n loader and resolver.

Loads RU / EN / HE locale dictionaries and exposes a recursive resolver that
walks an arbitrary Pydantic-derived dict and, wherever it finds a field ending
in `i18n_key` or `i18n_keys`, adds a sibling `i18n_text` / `i18n_texts` with
the resolved string in the requested locale.

The original key is preserved — never replaced — so:
  - audit log retains stable, locale-independent keys
  - the same assessment can be re-rendered in another locale without re-running
    the agent
  - admin/research overlay can show both key and text

RTL flag is exposed on the meta header so the frontend can mirror layout for
Hebrew without inferring direction from content.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional


# ----- Supported locales -----
SUPPORTED_LOCALES = ("ru", "en", "he")
DEFAULT_LOCALE = "ru"

ENV_I18N_DIR = "METACOD_GLP1_I18N_DIR"
LOCALE_FILE_PATTERN = "i18n_glp1_{locale}.json"


class I18nCache:
    """Process-level singleton holding all locale dictionaries."""

    def __init__(self) -> None:
        self._locales: dict[str, dict] = {}
        self._loaded: bool = False

    def load_locale(self, locale: str, path: str | Path) -> dict:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self._locales[locale] = data
        return data

    def load_all(self, base_dir: Optional[str | Path] = None) -> dict[str, dict]:
        """Load every supported locale from base_dir."""
        base = Path(base_dir) if base_dir else Path(os.environ.get(ENV_I18N_DIR, Path.cwd()))
        for loc in SUPPORTED_LOCALES:
            path = base / LOCALE_FILE_PATTERN.format(locale=loc)
            if path.exists():
                self.load_locale(loc, path)
        self._loaded = True
        return self._locales

    def get(self, locale: str) -> dict:
        if not self._loaded:
            raise RuntimeError(
                "I18nCache not initialised. Call load_all() during app startup."
            )
        if locale not in self._locales:
            return self._locales.get(DEFAULT_LOCALE, {})
        return self._locales[locale]

    def available_locales(self) -> list[str]:
        return list(self._locales.keys())

    def direction(self, locale: str) -> str:
        """Return 'rtl' or 'ltr' from the locale's _meta block."""
        meta = self.get(locale).get("_meta", {})
        return meta.get("direction", "ltr")


i18n_cache = I18nCache()


# ----- Resolver -----

def _lookup(key: str, locale_dict: dict, fallback_dict: Optional[dict] = None) -> str:
    """Resolve a single i18n key. Falls back to default locale if missing.

    If the key is not found in either, returns the key itself surrounded by [[ ]]
    so missing keys are visible in the UI without crashing.
    """
    text = locale_dict.get(key)
    if text is not None:
        return text
    if fallback_dict is not None:
        text = fallback_dict.get(key)
        if text is not None:
            return text
    return f"[[{key}]]"


def resolve_i18n(
    payload: Any,
    locale: str = DEFAULT_LOCALE,
    fallback_locale: str = DEFAULT_LOCALE,
) -> Any:
    """Recursively walk a dict / list / scalar and resolve all i18n keys.

    For every key in a dict:
      - `i18n_key` (string): adds sibling `i18n_text` with resolved string
      - `*_i18n_key` (string): adds sibling `*_i18n_text`
      - `*_i18n_keys` (list of strings): adds sibling `*_i18n_texts`

    Original keys are preserved.
    """
    locale_dict = i18n_cache.get(locale)
    fallback = i18n_cache.get(fallback_locale) if fallback_locale != locale else None

    return _walk(payload, locale_dict, fallback)


def _walk(node: Any, locale_dict: dict, fallback: Optional[dict]) -> Any:
    if isinstance(node, dict):
        out: dict = {}
        for k, v in node.items():
            out[k] = _walk(v, locale_dict, fallback)
            # Auto-resolve sibling text fields
            if isinstance(v, str):
                if k == "i18n_key":
                    out["i18n_text"] = _lookup(v, locale_dict, fallback)
                elif k == "i18n_key_internal":
                    # admin_trace uses this distinctive name; resolve it alongside
                    out["i18n_text_internal"] = _lookup(v, locale_dict, fallback)
                elif k.endswith("_i18n_key"):
                    text_key = k[: -len("_i18n_key")] + "_i18n_text"
                    out[text_key] = _lookup(v, locale_dict, fallback)
            elif isinstance(v, list) and k.endswith("_i18n_keys"):
                if all(isinstance(item, str) for item in v):
                    text_key = k[: -len("_i18n_keys")] + "_i18n_texts"
                    out[text_key] = [_lookup(item, locale_dict, fallback) for item in v]
        return out
    if isinstance(node, list):
        return [_walk(item, locale_dict, fallback) for item in node]
    return node


# ----- FastAPI dependency -----

def get_locale_dict(locale: str = DEFAULT_LOCALE) -> dict:
    return i18n_cache.get(locale)
