"""Tests for infra.i18n.I18n and its module-level convenience functions."""

import json
from pathlib import Path

from infra.i18n import I18n, get_i18n
from infra.i18n import t as t_


def _make_catalog_dir(tmp_path: Path) -> Path:
    """Build a small, self-contained locale tree.

    Kept independent of the shipped `locales/` catalog so fallback and
    interpolation behavior can be asserted precisely, without depending on
    which domain catalog files other modules add later.
    """
    base = tmp_path / "locales"

    en_dir = base / "en"
    en_dir.mkdir(parents=True)
    (en_dir / "common.json").write_text(
        json.dumps(
            {
                "greeting.hello": "Hello, {name}!",
                "only.in.en": "only in en",
                "no.params.here": "static text",
            }
        ),
        encoding="utf-8",
    )

    ja_dir = base / "ja"
    ja_dir.mkdir(parents=True)
    (ja_dir / "common.json").write_text(
        json.dumps({"greeting.hello": "こんにちは、{name}さん！"}, ensure_ascii=False),
        encoding="utf-8",
    )

    zh_dir = base / "zh"
    zh_dir.mkdir(parents=True)
    (zh_dir / "common.json").write_text(
        json.dumps({"greeting.hello": "你好，{name}！"}, ensure_ascii=False),
        encoding="utf-8",
    )

    return base


def test_default_locale_is_en():
    assert I18n().locale == "en"


def test_default_base_dir_resolves_to_repo_locales_regardless_of_cwd(monkeypatch, tmp_path):
    # base_dir defaults relative to this file's parent (repo root), not cwd.
    monkeypatch.chdir(tmp_path)
    i18n = I18n()
    assert i18n.t("common.yes") == "Yes"


def test_ja_override_returns_ja_value():
    assert I18n(locale="ja").t("common.yes") == "はい"


def test_zh_override_returns_zh_value():
    assert I18n(locale="zh").t("common.yes") == "是"


def test_missing_ja_key_falls_back_to_en(tmp_path):
    base = _make_catalog_dir(tmp_path)
    i18n = I18n(locale="ja", base_dir=base)

    assert i18n.t("only.in.en") == "only in en"


def test_missing_zh_key_falls_back_to_en(tmp_path):
    base = _make_catalog_dir(tmp_path)
    i18n = I18n(locale="zh", base_dir=base)

    assert i18n.t("only.in.en") == "only in en"


def test_missing_key_everywhere_returns_the_key_itself(tmp_path):
    base = _make_catalog_dir(tmp_path)
    i18n = I18n(locale="ja", base_dir=base)

    assert i18n.t("totally.unknown.key") == "totally.unknown.key"


def test_interpolation_with_params(tmp_path):
    base = _make_catalog_dir(tmp_path)
    i18n = I18n(locale="ja", base_dir=base)

    assert i18n.t("greeting.hello", name="Bob") == "こんにちは、Bobさん！"


def test_missing_param_leaves_template_intact(tmp_path):
    base = _make_catalog_dir(tmp_path)
    i18n = I18n(locale="en", base_dir=base)

    # No `name` kwarg supplied -> must not raise, returns the raw template.
    assert i18n.t("greeting.hello") == "Hello, {name}!"


def test_static_key_without_params_is_unchanged(tmp_path):
    base = _make_catalog_dir(tmp_path)
    i18n = I18n(locale="en", base_dir=base)

    assert i18n.t("no.params.here") == "static text"


def test_available_locales_includes_en_ja_and_zh():
    locales = I18n().available_locales()
    assert {"en", "ja", "zh"} <= set(locales)


def test_available_locales_reflects_custom_base_dir(tmp_path):
    base = _make_catalog_dir(tmp_path)
    assert I18n(base_dir=base).available_locales() == ["en", "ja", "zh"]


def test_with_locale_switches_bound_locale(tmp_path):
    base = _make_catalog_dir(tmp_path)
    en = I18n(locale="en", base_dir=base)
    ja = en.with_locale("ja")

    assert en.locale == "en"
    assert ja.locale == "ja"
    assert ja.t("greeting.hello", name="Bob") == "こんにちは、Bobさん！"
    # Switching returns a new bound copy; the original is unaffected.
    assert en.t("greeting.hello", name="Bob") == "Hello, Bob!"


def test_module_level_get_i18n_defaults_to_en():
    i18n = get_i18n()
    assert i18n.locale == "en"
    assert i18n.t("common.yes") == "Yes"


def test_module_level_get_i18n_accepts_locale_override():
    assert get_i18n("ja").locale == "ja"


def test_module_level_t_supports_locale_kwarg():
    assert t_("common.yes") == "Yes"
    assert t_("common.yes", locale="ja") == "はい"


def test_module_level_t_missing_key_returns_key():
    assert t_("totally.unknown.key") == "totally.unknown.key"
