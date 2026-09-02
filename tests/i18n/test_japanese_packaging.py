"""Packaging regressions for the Japanese locale catalog."""

import tomllib
from pathlib import Path


def test_setuptools_includes_japanese_locale_catalogs():
    root = Path(__file__).resolve().parents[2]
    config = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))

    setuptools = config["tool"]["setuptools"]
    assert "locales.ja" in setuptools["packages"]
    assert setuptools["package-data"]["locales.ja"] == ["*.json"]
