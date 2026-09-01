"""Japanese command aliases layered over the core EN/ZH command router.

The core router and ``CommandSpec`` remain wire-compatible with upstream. This
module adds a Japanese input dialect, Japanese-first help rendering, and the
third room locale to the package-level ``CommandRouter`` exported by
:mod:`gateway.commands`.
"""

from __future__ import annotations

from typing import Any

from gateway.commands.rooms import _is_keeper
from gateway.commands.router import CommandRouter as _CoreCommandRouter
from gateway.commands.router import _COMMAND_TOKEN_RE
from gateway.commands.types import CommandCtx, CommandSpec
from infra.i18n import get_i18n


JAPANESE_COMMAND_ALIASES: dict[str, tuple[str, ...]] = {
    "roll": ("ダイス", "ロール"),
    "hidden_roll": ("秘匿ダイス", "シークレットダイス"),
    "check": ("判定", "チェック"),
    "opposed": ("対抗判定",),
    "sheet": ("キャラシート", "シート"),
    "npc": ("NPC", "登場人物"),
    "companion": ("同行者", "コンパニオン"),
    "panel": ("パネル",),
    "language": ("言語",),
    "bind": ("紐付け",),
    "unbind": ("紐付け解除",),
    "init": ("イニシアチブ", "行動順"),
    "genchar": ("キャラ作成", "キャラクター作成"),
    "rule": ("ルール",),
    "rename": ("名前変更",),
    "jrrp": ("運勢", "今日の運勢"),
    "draw": ("ドロー", "カード"),
    "bot": ("ボット",),
    "skill": ("技能",),
    "phase": ("フェーズ",),
    "dev": ("開発",),
    "undo": ("取り消し", "巻き戻し"),
    "save": ("保存",),
    "habits": ("傾向", "習慣"),
    "panels": ("パネル一覧",),
    "pack": ("パック",),
    "avatar": ("アバター",),
    "audio": ("音声",),
    "bgm": ("音楽",),
    "ambience": ("環境音",),
    "sfx": ("効果音",),
    "botlist": ("ボット一覧",),
    "report": ("セッション記録", "レポート"),
    "recap": ("あらすじ", "振り返り"),
    "chronicle": ("年代記", "クロニクル"),
    "party": ("パーティー", "パーティ"),
    "lore": ("ロア", "世界設定"),
    "import": ("インポート",),
    "var": ("変数",),
    "pc": ("PC一覧", "キャラ一覧"),
    "preset": ("プリセット",),
    "module": ("モジュール", "シナリオ導入"),
    "room": ("部屋", "ルーム"),
    "reset": ("リセット",),
    "model": ("モデル",),
    "help": ("ヘルプ",),
}

_LANGUAGE_ALIASES = {
    "en": "en",
    "english": "en",
    "英語": "en",
    "zh": "zh",
    "中文": "zh",
    "中国語": "zh",
    "簡体字中国語": "zh",
    "ja": "ja",
    "jp": "ja",
    "japanese": "ja",
    "日本語": "ja",
}


def _is_ja(locale: str) -> bool:
    return locale.casefold().startswith("ja")


class CommandRouter(_CoreCommandRouter):
    """Core router plus a Japanese command-name and locale dialect."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._alias_maps["ja"] = self._build_ja_alias_map(self._specs)

    def _build_ja_alias_map(self, specs: list[CommandSpec]) -> dict[str, CommandSpec]:
        by_canonical = {spec.canonical: spec for spec in specs}
        alias_map: dict[str, CommandSpec] = {}
        for canonical, aliases in JAPANESE_COMMAND_ALIASES.items():
            spec = by_canonical.get(canonical)
            if spec is None:
                continue
            for alias in aliases:
                token = alias.casefold()
                existing = alias_map.get(token)
                if existing is not None and existing is not spec:
                    raise ValueError(
                        f"Japanese command alias {alias!r} is claimed by both "
                        f"{existing.canonical!r} and {canonical!r}"
                    )
                alias_map[token] = spec
        return alias_map

    def refresh_pack_words(self, *, force: bool = False) -> bool:
        changed = super().refresh_pack_words(force=force)
        if changed:
            self._alias_maps["ja"] = self._build_ja_alias_map(self._specs)
        return changed

    def resolve(self, text: str, locale: str) -> tuple[CommandSpec, str] | None:
        if _is_ja(locale):
            stripped = text.strip()
            prefix = next((item for item in self.prefixes if stripped.startswith(item)), "")
            if prefix:
                rest = stripped[len(prefix) :].lstrip()
                match = _COMMAND_TOKEN_RE.match(rest)
                if match:
                    token = match.group(1).casefold()
                    spec = self._alias_maps["ja"].get(token)
                    if spec is not None:
                        return spec, (match.group(2) or "").strip()
        # English aliases, Chinese aliases, inline rolls, and dynamically
        # discovered rule-pack words continue through the upstream path.
        return super().resolve(text, locale)

    async def cmd_language(self, ctx: CommandCtx) -> str:
        """Set the shared room locale, accepting Japanese language names as aliases."""
        locale = _LANGUAGE_ALIASES.get(ctx.args.strip().casefold())
        if locale is None:
            return ctx.i18n.t("commands.language.usage")
        if not _is_keeper(ctx.raw_ctx):
            return ctx.fail(ctx.i18n.t("rooms.denied"))
        await ctx.services.store.state_set(ctx.chat_key, "chat_locale", locale)
        ctx.raw_ctx.locale = locale
        return get_i18n(locale).t("commands.language.done")

    async def cmd_help(self, ctx: CommandCtx) -> str:
        if not _is_ja(ctx.locale):
            return await super().cmd_help(ctx)

        prefix = ctx.router.prefixes[0]
        player_names: list[str] = []
        keeper_names: list[str] = []
        for spec in self._specs:
            aliases = JAPANESE_COMMAND_ALIASES.get(spec.canonical, tuple(spec.aliases_en))
            name = f"{prefix}{aliases[0]}"
            if spec.keeper_help or spec.required_level:
                keeper_names.append(name)
            else:
                player_names.append(name)

        lines = [ctx.i18n.t("commands.help.result", commands=", ".join(player_names))]
        if _is_keeper(ctx.raw_ctx):
            if keeper_names:
                lines.append(ctx.i18n.t("commands.help.keeper_section", commands=", ".join(keeper_names)))
        else:
            lines.append(ctx.i18n.t("commands.help.player_hint"))
        return "\n".join(lines)
