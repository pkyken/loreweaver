"""Platform-independent command router with EN, CN, and JP dialects.

A package since 2026-08-19: `router` holds the core spec table and dispatch, and each
command domain is its own module composed into the core router as a mixin (`checks`,
`sheet`, `rules`, `rooms`, `cast`, `world`, `panels`, `media`, `llm`). The public
`CommandRouter` adds the Japanese input dialect without changing the upstream
`CommandSpec` wire shape. Import the public names from here; monkeypatch a helper
where it is DEFINED (e.g. `gateway.commands.llm.flow_for`).
"""

from __future__ import annotations

from gateway.commands.japanese import CommandRouter
from gateway.commands.types import CommandCtx, CommandReply, CommandSpec

__all__ = ["CommandCtx", "CommandReply", "CommandRouter", "CommandSpec"]
