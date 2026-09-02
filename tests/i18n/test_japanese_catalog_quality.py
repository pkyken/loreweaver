from __future__ import annotations

import json
import string
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[2]
_LOCALES = _REPO_ROOT / "locales"

# These values intentionally contain only placeholders, separators, or other
# language-neutral formatting. Keeping the Japanese value identical is correct;
# translating them would add noise without changing anything shown to players.
_INTENTIONALLY_IDENTICAL_PRIORITY_VALUES = {
    "battle.json:battle.report.md.stat_row",
    "battle.json:battle.report.stat_line",
    "commands.json:commands.panel.list_item",
    "companion.json:companion.sheet.name_line",
    "kp_tools.json:kp_tools.character.sheet.field_line",
    "kp_tools.json:kp_tools.character.sheet.meter_line",
    "kp_tools.json:kp_tools.character.sheet.skill_line",
    "kp_tools.json:kp_tools.dice.hp.status_line",
    "kp_tools.json:kp_tools.dice.skill_check.modifier_line",
    "kp_tools.json:kp_tools.initiative.list_item",
    "kp_tools.json:kp_tools.know.clock.event_line",
    "kp_tools.json:kp_tools.know.note.get_done",
    "kp_tools.json:kp_tools.know.note.list_item",
    "kp_tools.json:kp_tools.know.search.divider",
    "kp_tools.json:kp_tools.know.summary.truth_item",
    "kp_tools.json:kp_tools.subsystem.draw.result",
    "kp_tools.json:kp_tools.subsystem.script_roll_line",
    "prompt.json:prompt.divider",
    "prompt.json:prompt.game_state.clue_line",
    "prompt.json:prompt.game_state.solo_line",
}


def _catalog_files(locale: str) -> dict[str, Path]:
    directory = _LOCALES / locale
    return {path.name: path for path in sorted(directory.glob("*.json"))}


def _load(path: Path) -> dict[str, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict), path
    assert all(isinstance(key, str) and isinstance(value, str) for key, value in data.items()), path
    return data


def _fields(template: str) -> set[str]:
    fields: set[str] = set()
    for _, field_name, _, _ in string.Formatter().parse(template):
        if field_name:
            fields.add(field_name.split("!", 1)[0].split(":", 1)[0])
    return fields


def test_japanese_catalog_has_file_and_key_parity_with_english() -> None:
    english_files = _catalog_files("en")
    japanese_files = _catalog_files("ja")

    assert japanese_files.keys() == english_files.keys()
    for filename, english_path in english_files.items():
        english = _load(english_path)
        japanese = _load(japanese_files[filename])
        assert japanese.keys() == english.keys(), filename


def test_japanese_catalog_values_are_non_empty_and_preserve_placeholders() -> None:
    english_files = _catalog_files("en")
    japanese_files = _catalog_files("ja")

    for filename, english_path in english_files.items():
        english = _load(english_path)
        japanese = _load(japanese_files[filename])
        for key, english_value in english.items():
            japanese_value = japanese[key]
            assert japanese_value.strip(), f"{filename}:{key}"
            assert _fields(japanese_value) == _fields(english_value), f"{filename}:{key}"


def test_priority_player_facing_catalogs_are_not_untranslated_copies() -> None:
    # Technical literals and structured command tokens may intentionally remain
    # identical. Long natural-language values in these high-traffic catalogs may not.
    priority = ("battle.json", "commands.json", "companion.json", "kp_tools.json", "prompt.json")
    untranslated: list[str] = []

    for filename in priority:
        english = _load(_LOCALES / "en" / filename)
        japanese = _load(_LOCALES / "ja" / filename)
        for key, english_value in english.items():
            entry = f"{filename}:{key}"
            if entry in _INTENTIONALLY_IDENTICAL_PRIORITY_VALUES:
                continue
            if len(english_value.strip()) < 16:
                continue
            if english_value == japanese[key]:
                untranslated.append(entry)

    assert not untranslated, "Untranslated Japanese values:\n" + "\n".join(untranslated)
