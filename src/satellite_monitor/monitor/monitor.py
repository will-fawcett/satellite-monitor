"""Advanced satellite monitoring with orbit predictions."""

from __future__ import annotations

import logging
from dataclasses import field
from datetime import datetime, timedelta, timezone
import pandas as pd

from ..core.location import Area, Location
from ..core.passes import SatellitePass
from ..core.providers import SatelliteProvider, get_provider_url
from ..core.satellites import SATELLITE_CATALOG, SatelliteSpecs

logger = logging.getLogger(__name__)


class SatelliteMonitor:
    """Main monitoring system for satellite passes and data availability.

    Provides advanced monitoring capabilities including pass predictions,
    cost estimation, and coverage analysis for a target location.
    """

    def __init__(
        self,
        location: Location | None = None,
        area: Area | None = None
    ):
        """Initialize the satellite monitor.

        Args:
            location: Target location for monitoring. Defaults to Brussels.
            area: Coverage area for cost calculations. Defaults to Brussels area.
        """
        self.location = location or Location.brussels()
        self.area = area or Area.brussels()
        self.passes_cache: list[SatellitePass] = []
        self.last_update = datetime.now(timezone.utc)

    def calculate_next_passes(self, hours_ahead: int = 48) -> list[SatellitePass]:
        """Calculate upcoming satellite passes for all constellations.

        Args:
            hours_ahead: How many hours ahead to calculate

        Returns:
            List of SatellitePass objects sorted by time
        """
        passes = []
        now = datetime.now(timezone.utc)
        end_time = now + timedelta(hours=hours_ahead)

        for constellation_name, specs in SATELLITE_CATALOG.items():
            logger.debug(f"Calculating passes for {constellation_name}")

            # Estimate passes based on revisit time
            revisit_hours = specs.revisit_time_days * 24
            next_pass_time = now

            while next_pass_time < end_time:
                # Calculate estimated cost
                min_cost, max_cost = specs.estimate_cost(self.area.area_sqkm)

                pass_info = SatellitePass(
                    satellite_name=(
                        specs.satellites[0] if specs.satellites else constellation_name
                    ),
                    constellation=constellation_name,
                    provider=specs.provider,
                    pass_time=next_pass_time,
                    duration_seconds=300,  # Approximate 5-minute pass
                    max_elevation_deg=75,  # Simplified
                    azimuth_deg=180,  # Simplified
                    image_available=True,
                    expected_cloud_coverage=None if specs.has_sar else 15.0,
                    resolution_m=specs.resolution_m,
                    cost_estimate_usd=(min_cost, max_cost),
                    data_latency_hours=specs.data_latency_hours,
                    ordering_url=get_provider_url(specs.provider),
                )
                passes.append(pass_info)
                next_pass_time += timedelta(hours=revisit_hours)

        # Sort by pass time
        passes.sort(key=lambda x: x.pass_time)
        self.passes_cache = passes
        return passes

    def get_last_available_images(self) -> dict[str, dict]:
        """Get information about the last available image from each provider.

        Returns:
            Dictionary mapping constellation name to image info
        """
        last_images = {}

        for constellation_name, specs in SATELLITE_CATALOG.items():
            now = datetime.now(timezone.utc)
            last_pass = now - timedelta(days=specs.revisit_time_days)
            available_time = last_pass + timedelta(hours=specs.data_latency_hours[1])
            min_cost, max_cost = specs.estimate_cost(self.area.area_sqkm)

            last_images[constellation_name] = {
                "provider": specs.provider.value,
                "last_acquisition": last_pass.isoformat(),
                "data_available_since": available_time.isoformat(),
                "resolution_m": specs.resolution_m,
                "cost_estimate_usd": (min_cost, max_cost),
                "free": specs.free_tier,
                "has_sar": specs.has_sar,
                "ordering_url": get_provider_url(specs.provider),
            }

        return last_images

    def get_next_opportunities(self, hours: int = 24) -> pd.DataFrame:
        """Get next imaging opportunities as a DataFrame.

        Args:
            hours: How many hours ahead to look

        Returns:
            DataFrame with columns for constellation, provider, time, etc.
        """
        passes = self.calculate_next_passes(hours)

        data = []
        for p in passes:
            data.append({
                "Constellation": p.constellation,
                "Provider": p.provider.value,
                "Pass Time (UTC)": p.pass_time.strftime("%Y-%m-%d %H:%M"),
                "Resolution (m)": p.resolution_m,
                "Min Cost (USD)": f"${p.cost_estimate_usd[0]:.2f}",
                "Max Cost (USD)": f"${p.cost_estimate_usd[1]:.2f}",
                "Free": p.cost_estimate_usd[0] == 0,
                "Data Ready In": f"{p.data_latency_hours[0]}-{p.data_latency_hours[1]}h",
                "Has SAR": p.constellation in ["ICEYE", "Capella", "Sentinel-1"],
                "Weather Independent": p.is_weather_independent,
            })

        return pd.DataFrame(data)

    def estimate_total_coverage_cost(
        self,
        resolution_m: float = 1.0,
        frequency_days: int = 1,
        duration_months: int = 1,
    ) -> dict[str, dict]:
        """Estimate cost for continuous coverage.

        Args:
            resolution_m: Maximum acceptable resolution in meters
            frequency_days: How often images are needed
            duration_months: Coverage duration in months

        Returns:
            Dictionary mapping satellite name to cost info
        """
        costs = {}
        images_needed = (30 * duration_months) / frequency_days

        for name, specs in SATELLITE_CATALOG.items():
            if (
                specs.resolution_m <= resolution_m and
                specs.revisit_time_days <= frequency_days
            ):
                min_cost, max_cost = specs.estimate_cost(self.area.area_sqkm)
                costs[name] = {
                    "min_monthly_usd": min_cost * images_needed,
                    "max_monthly_usd": max_cost * images_needed,
                    "resolution_m": specs.resolution_m,
                    "actual_frequency_days": specs.revisit_time_days,
                }

        return costs

    def format_report(self) -> str:
        """Generate a formatted text report of satellite availability.

        Returns:
            Multi-line string report
        """
        report = []
        report.append("=" * 80)
        report.append(f"SATELLITE IMAGERY AVAILABILITY REPORT - {self.location.name.upper()}")
        report.append("=" * 80)
        report.append(
            f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"
        )
        report.append(f"Coverage Area: ~{self.area.area_sqkm:.1f} km2")
        report.append("")

        # Last available images
        report.append("LAST AVAILABLE IMAGES")
        report.append("-" * 40)
        last_images = self.get_last_available_images()

        for constellation, info in sorted(
            last_images.items(), key=lambda x: x[1]["cost_estimate_usd"][0]
        ):
            report.append(f"\n{constellation}:")
            report.append(f"  Provider: {info['provider']}")
            report.append(f"  Last Acquisition: {info['last_acquisition'][:16]}")
            report.append(f"  Data Available Since: {info['data_available_since'][:16]}")
            report.append(f"  Resolution: {info['resolution_m']}m")
            if info["free"]:
                report.append("  Cost: FREE")
            else:
                report.append(
                    f"  Cost Estimate: ${info['cost_estimate_usd'][0]:.2f} - "
                    f"${info['cost_estimate_usd'][1]:.2f}"
                )
            if info["has_sar"]:
                report.append("  Type: SAR (works through clouds)")

        report.append("\n" + "=" * 80)
        report.append("NEXT 24 HOURS - IMAGING OPPORTUNITIES")
        report.append("-" * 40)

        df = self.get_next_opportunities(24)
        report.append(df.to_string(index=False))

        # Cost comparison
        report.append("\n" + "=" * 80)
        report.append("MONTHLY MONITORING COST COMPARISON (Daily Coverage)")
        report.append("-" * 40)

        costs = self.estimate_total_coverage_cost(
            resolution_m=5.0, frequency_days=1, duration_months=1
        )
        for provider, cost_info in sorted(
            costs.items(), key=lambda x: x[1]["min_monthly_usd"]
        ):
            if cost_info["min_monthly_usd"] == 0:
                report.append(
                    f"{provider:15} - FREE (Resolution: {cost_info['resolution_m']}m)"
                )
            else:
                report.append(
                    f"{provider:15} - ${cost_info['min_monthly_usd']:,.0f} - "
                    f"${cost_info['max_monthly_usd']:,.0f}/month "
                    f"(Resolution: {cost_info['resolution_m']}m)"
                )

        return "\n".join(report)
