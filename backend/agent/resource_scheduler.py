"""Resource scheduler – async semaphores for CPU, GPU, and remote API lanes."""

from __future__ import annotations

import asyncio
import os


RESOURCE_LIMITS = {
    "cpu": int(os.getenv("RESOURCE_LIMIT_CPU", "8")),
    "local_gpu_light": int(os.getenv("RESOURCE_LIMIT_LOCAL_GPU_LIGHT", "1")),
    "remote_api": int(os.getenv("RESOURCE_LIMIT_REMOTE_API", "4")),
}

# Semaphores are created lazily per event loop
_semaphores: dict[str, asyncio.Semaphore] = {}


def get_semaphore(lane: str) -> asyncio.Semaphore:
    """Get or create a semaphore for the given resource lane."""
    if lane not in _semaphores:
        limit = RESOURCE_LIMITS.get(lane, RESOURCE_LIMITS["cpu"])
        _semaphores[lane] = asyncio.Semaphore(limit)
    return _semaphores[lane]


def reset_semaphores():
    """Reset semaphores (useful for testing)."""
    _semaphores.clear()
