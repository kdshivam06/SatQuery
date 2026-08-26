"""Base protocol for SatQuery executable tools."""

from __future__ import annotations

from typing import Protocol


class Tool(Protocol):
    name: str
    description: str
    resource: str

    async def run(self, context: dict, params: dict, prior_results: dict) -> dict:
        ...
