"""Sentinel data download functionality.

This module requires optional dependencies. Install with:
    pip install satellite-monitor[sentinel]
"""

from __future__ import annotations

from typing import TYPE_CHECKING

# Lazy imports with helpful error messages


def __getattr__(name: str):
    """Lazy import with helpful error messages for missing dependencies."""
    if name in ("SentinelDownloader", "SentinelConfig"):
        try:
            from .sentinel import SentinelConfig, SentinelDownloader
            return SentinelDownloader if name == "SentinelDownloader" else SentinelConfig
        except ImportError as e:
            raise ImportError(
                f"{name} requires the 'sentinel' optional dependencies. "
                "Install with: pip install satellite-monitor[sentinel]"
            ) from e

    if name == "download_latest_sentinel":
        try:
            from .quick import download_latest_sentinel
            return download_latest_sentinel
        except ImportError as e:
            raise ImportError(
                f"{name} requires the 'sentinel' optional dependencies. "
                "Install with: pip install satellite-monitor[sentinel]"
            ) from e

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "SentinelDownloader",
    "SentinelConfig",
    "download_latest_sentinel",
]
