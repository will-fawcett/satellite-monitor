"""Satellite pass information."""

from dataclasses import dataclass
from datetime import datetime

from .providers import SatelliteProvider


@dataclass
class SatellitePass:
    """Information about a satellite pass over a location.

    Attributes:
        satellite_name: Name of the specific satellite
        constellation: Name of the satellite constellation
        provider: Satellite operator/data provider
        pass_time: UTC datetime of the pass
        duration_seconds: Duration of the pass in seconds
        max_elevation_deg: Maximum elevation angle in degrees
        azimuth_deg: Azimuth angle in degrees
        image_available: Whether imagery will be collected
        expected_cloud_coverage: Expected cloud coverage percentage (None for SAR)
        resolution_m: Spatial resolution in meters
        cost_estimate_usd: (min, max) cost estimate in USD
        data_latency_hours: (min, max) hours until data available
        ordering_url: URL to order/access the data
    """
    satellite_name: str
    constellation: str
    provider: SatelliteProvider
    pass_time: datetime
    duration_seconds: float
    max_elevation_deg: float
    azimuth_deg: float
    image_available: bool
    expected_cloud_coverage: float | None
    resolution_m: float
    cost_estimate_usd: tuple[float, float]
    data_latency_hours: tuple[float, float]
    ordering_url: str | None

    @property
    def is_free(self) -> bool:
        """Check if this pass data is free."""
        return self.cost_estimate_usd[0] == 0 and self.cost_estimate_usd[1] == 0

    @property
    def is_weather_independent(self) -> bool:
        """Check if this satellite works regardless of weather (SAR)."""
        return self.expected_cloud_coverage is None

    def format_cost(self) -> str:
        """Format cost estimate as human-readable string."""
        if self.is_free:
            return "FREE"
        min_cost, max_cost = self.cost_estimate_usd
        if min_cost == max_cost:
            return f"${min_cost:,.0f}"
        return f"${min_cost:,.0f} - ${max_cost:,.0f}"

    def format_latency(self) -> str:
        """Format data latency as human-readable string."""
        min_h, max_h = self.data_latency_hours
        if min_h == max_h:
            return f"{min_h}h"
        return f"{min_h}-{max_h}h"
