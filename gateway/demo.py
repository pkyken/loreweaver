"""Shared recognition helpers for the built-in offline demo workflow."""

from __future__ import annotations

from infra.i18n import get_i18n

_LEGACY_SETUP_REQUESTS = ("upload the demo module",)  # i18n-exempt: parser tokens


def is_guided_demo_request(text: str) -> bool:
    """Whether the scripted fallback received an explicit guided setup action."""
    lowered = text.strip().casefold()
    i18n = get_i18n()
    return lowered in {
        i18n.with_locale(locale).t("tui.demo.action").casefold()
        for locale in i18n.available_locales()
    }


def is_demo_setup_request(text: str) -> bool:
    """Whether the fallback would invoke its destructive sample-module setup tools."""
    lowered = text.strip().casefold()
    return is_guided_demo_request(lowered) or lowered in _LEGACY_SETUP_REQUESTS
