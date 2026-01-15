"""Quick download utilities for Sentinel data."""

from __future__ import annotations

import logging
from pathlib import Path
from ..core.location import Area
from .sentinel import SentinelConfig, SentinelDownloader

logger = logging.getLogger(__name__)


def download_latest_sentinel(
    area: Area | None = None,
    output_dir: Path | None = None,
    days_back: int = 30,
    max_cloud_coverage: int = 20,
    max_products: int = 3,
    dry_run: bool = False
) -> dict:
    """Download the latest Sentinel data for an area.

    Credentials are read from environment variables:
        COPERNICUS_USERNAME
        COPERNICUS_PASSWORD

    Args:
        area: Target area. Defaults to Brussels.
        output_dir: Download directory. Defaults to ./sentinel_data
        days_back: How many days back to search
        max_cloud_coverage: Maximum cloud coverage for optical imagery
        max_products: Maximum products per satellite type
        dry_run: If True, search only without downloading

    Returns:
        Dictionary with download summary

    Raises:
        ImportError: If sentinel dependencies not installed
        ValueError: If credentials not configured
    """
    config = SentinelConfig.from_env(
        download_dir=output_dir or Path("./sentinel_data"),
        days_back=days_back,
        max_cloud_coverage=max_cloud_coverage,
        max_products=max_products
    )

    if not config.username or not config.password:
        raise ValueError(
            "Copernicus Hub credentials not configured.\n"
            "Set environment variables:\n"
            "  export COPERNICUS_USERNAME='your_username'\n"
            "  export COPERNICUS_PASSWORD='your_password'\n\n"
            "Register at: https://scihub.copernicus.eu/dhus/#/self-registration"
        )

    downloader = SentinelDownloader(config, area=area)

    try:
        s1_df, s2_df = downloader.run(download=not dry_run)

        return {
            "success": True,
            "sentinel1_count": len(s1_df),
            "sentinel2_count": len(s2_df),
            "output_dir": str(config.download_dir),
            "area": area.name if area else "Brussels",
            "downloaded": not dry_run
        }

    except Exception as e:
        logger.error(f"Download failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }
