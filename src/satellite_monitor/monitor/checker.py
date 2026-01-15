"""Quick satellite availability checker."""

from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from rich import box
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

from ..core.location import Location
from ..weather.models import WeatherData
from ..weather.service import WeatherService


# Default satellite configurations with realistic timing
DEFAULT_SATELLITES = {
    # Free/Public satellites
    "Sentinel-1A": {
        "provider": "ESA Copernicus",
        "type": "SAR",
        "resolution_m": 5,
        "revisit_days": 6,
        "last_pass_hours_ago": 36,
        "data_latency_hours": 3,
        "cost_per_sqkm": 0,
        "weather_independent": True
    },
    "Sentinel-2A": {
        "provider": "ESA Copernicus",
        "type": "Optical",
        "resolution_m": 10,
        "revisit_days": 5,
        "last_pass_hours_ago": 24,
        "data_latency_hours": 3,
        "cost_per_sqkm": 0,
        "weather_independent": False
    },
    "Landsat-9": {
        "provider": "USGS",
        "type": "Optical",
        "resolution_m": 30,
        "revisit_days": 16,
        "last_pass_hours_ago": 120,
        "data_latency_hours": 24,
        "cost_per_sqkm": 0,
        "weather_independent": False
    },
    # Commercial satellites - High resolution
    "WorldView-3": {
        "provider": "Maxar",
        "type": "Optical",
        "resolution_m": 0.31,
        "revisit_days": 1,
        "last_pass_hours_ago": 8,
        "data_latency_hours": 12,
        "cost_per_sqkm": 25,
        "weather_independent": False
    },
    "Pleiades-Neo": {
        "provider": "Airbus",
        "type": "Optical",
        "resolution_m": 0.30,
        "revisit_days": 1,
        "last_pass_hours_ago": 14,
        "data_latency_hours": 6,
        "cost_per_sqkm": 30,
        "weather_independent": False
    },
    # Commercial satellites - Daily monitoring
    "PlanetScope": {
        "provider": "Planet Labs",
        "type": "Optical",
        "resolution_m": 3.0,
        "revisit_days": 1,
        "last_pass_hours_ago": 4,
        "data_latency_hours": 2,
        "cost_per_sqkm": 2.5,
        "weather_independent": False
    },
    "SkySat": {
        "provider": "Planet Labs",
        "type": "Optical",
        "resolution_m": 0.50,
        "revisit_days": 1,
        "last_pass_hours_ago": 6,
        "data_latency_hours": 3,
        "cost_per_sqkm": 10,
        "weather_independent": False
    },
    "BlackSky": {
        "provider": "BlackSky",
        "type": "Optical",
        "resolution_m": 1.0,
        "revisit_days": 1,
        "last_pass_hours_ago": 2,
        "data_latency_hours": 1,
        "cost_per_sqkm": 4.5,
        "weather_independent": False
    },
    # SAR satellites (work through clouds)
    "ICEYE-X": {
        "provider": "ICEYE",
        "type": "SAR",
        "resolution_m": 0.25,
        "revisit_days": 1,
        "last_pass_hours_ago": 10,
        "data_latency_hours": 2,
        "cost_per_sqkm": 100,
        "weather_independent": True
    },
    "Capella": {
        "provider": "Capella Space",
        "type": "SAR",
        "resolution_m": 0.5,
        "revisit_days": 1,
        "last_pass_hours_ago": 18,
        "data_latency_hours": 1,
        "cost_per_sqkm": 80,
        "weather_independent": True
    }
}


class SatelliteChecker:
    """Quick checker for satellite image availability.

    Provides weather-aware satellite availability information including
    pass times, costs, and recommendations based on current conditions.
    """

    def __init__(
        self,
        location: Location | None = None,
        area_sqkm: float = 100
    ):
        """Initialize the satellite checker.

        Args:
            location: Target location for satellite monitoring. Defaults to Brussels.
            area_sqkm: Coverage area in square kilometers for cost calculations.
        """
        self.location = location or Location.brussels()
        self.area_sqkm = area_sqkm
        self.console = Console()
        self.weather_service = WeatherService(location=self.location)
        self.current_weather: WeatherData | None = None
        self.satellites = DEFAULT_SATELLITES.copy()

    def calculate_times(self, satellite_data: dict) -> tuple[datetime, datetime, datetime]:
        """Calculate last image, next pass, and next available times.

        Args:
            satellite_data: Satellite configuration dictionary

        Returns:
            Tuple of (last_available, next_pass, next_available) datetimes
        """
        now = datetime.now(timezone.utc)

        # Last pass time
        last_pass = now - timedelta(hours=satellite_data["last_pass_hours_ago"])

        # Last image available time (pass + processing latency)
        last_image_available = last_pass + timedelta(
            hours=satellite_data["data_latency_hours"]
        )

        # Next pass time
        hours_until_next = (
            (satellite_data["revisit_days"] * 24) -
            satellite_data["last_pass_hours_ago"]
        )
        next_pass = now + timedelta(hours=max(0, hours_until_next))

        # Next image available time
        next_image_available = next_pass + timedelta(
            hours=satellite_data["data_latency_hours"]
        )

        return last_image_available, next_pass, next_image_available

    def format_time_delta(self, dt: datetime) -> str:
        """Format time difference from now as human-readable string."""
        now = datetime.now(timezone.utc)
        delta = dt - now

        if delta.total_seconds() < 0:
            # Past
            hours = abs(delta.total_seconds()) / 3600
            if hours < 1:
                return f"{int(hours * 60)}m ago"
            elif hours < 24:
                return f"{int(hours)}h ago"
            else:
                return f"{int(hours / 24)}d ago"
        else:
            # Future
            hours = delta.total_seconds() / 3600
            if hours < 1:
                return f"in {int(hours * 60)}m"
            elif hours < 24:
                return f"in {int(hours)}h"
            else:
                return f"in {int(hours / 24)}d"

    def calculate_cost(self, satellite_data: dict) -> str:
        """Calculate cost for the configured area."""
        cost_per_sqkm = satellite_data["cost_per_sqkm"]
        if cost_per_sqkm == 0:
            return "FREE"
        total_cost = cost_per_sqkm * self.area_sqkm
        return f"${total_cost:,.0f}"

    def get_current_weather(self) -> WeatherData | None:
        """Get current weather data.

        Returns:
            WeatherData if API configured, None otherwise.
        """
        if self.current_weather is None:
            self.current_weather = self.weather_service.get_weather()
        return self.current_weather

    def refresh_weather(self) -> WeatherData | None:
        """Force refresh of weather data."""
        self.current_weather = self.weather_service.get_weather()
        return self.current_weather

    def create_summary_table(self) -> Table:
        """Create summary table of all satellites."""
        weather = self.get_current_weather()
        has_weather = weather is not None

        if has_weather:
            cloud_cover = weather.current_cloud_cover
            is_day = weather.is_daylight
            day_emoji = "sunny" if is_day else "moon"
            title = (
                f"Satellite Image Availability for {self.location.name} | "
                f"Cloud Cover: {cloud_cover}% {day_emoji}"
            )
        else:
            cloud_cover = None
            is_day = None
            title = (
                f"Satellite Image Availability for {self.location.name} | "
                f"Weather: No API configured"
            )

        table = Table(
            title=title,
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan"
        )

        table.add_column("Satellite", style="bold", width=15)
        table.add_column("Provider", width=15)
        table.add_column("Type", width=8)
        table.add_column("Resolution", justify="right", width=10)
        table.add_column("Weather OK", justify="center", width=10)
        table.add_column("Last Image", width=12)
        table.add_column("Next Image", width=12)
        table.add_column("Cost/Image", justify="right", width=12)

        # Separate and sort satellites
        free_satellites = []
        commercial_satellites = []

        for name, data in self.satellites.items():
            last_available, _, next_available = self.calculate_times(data)
            cost = self.calculate_cost(data)

            # Assess weather suitability
            if not has_weather:
                # No weather data - show N/A for optical, "yes" for SAR (always works)
                if data["weather_independent"]:
                    weather_ok = "[green]yes[/green]"
                else:
                    weather_ok = "[dim]unknown[/dim]"
            elif data["weather_independent"]:
                weather_ok = "[green]yes[/green]"
            elif cloud_cover < 30 and is_day:
                weather_ok = "[green]yes[/green]"
            elif cloud_cover < 60 and is_day:
                weather_ok = "[yellow]marginal[/yellow]"
            else:
                weather_ok = "[red]no[/red]"

            row_data = [
                name,
                data["provider"],
                data["type"],
                f"{data['resolution_m']}m",
                weather_ok,
                self.format_time_delta(last_available),
                self.format_time_delta(next_available),
                cost
            ]

            if cost == "FREE":
                free_satellites.append(row_data)
            else:
                commercial_satellites.append((data["cost_per_sqkm"], row_data))

        # Sort commercial by cost
        commercial_satellites.sort(key=lambda x: x[0])

        # Add free satellites first
        for row in free_satellites:
            row[7] = f"[green]{row[7]}[/green]"
            table.add_row(*row)

        # Add separator
        if free_satellites and commercial_satellites:
            table.add_row(*["---"] * 8)

        # Add commercial satellites
        for _, row in commercial_satellites:
            cost_val = float(row[7].replace("$", "").replace(",", ""))
            if cost_val > 1000:
                row[7] = f"[red]{row[7]}[/red]"
            else:
                row[7] = f"[yellow]{row[7]}[/yellow]"
            table.add_row(*row)

        return table

    def create_next_available_panel(self) -> Panel:
        """Create panel showing next available images."""
        lines = []

        # Find next 5 images
        next_images = []
        for name, data in self.satellites.items():
            _, _, next_available = self.calculate_times(data)
            cost = self.calculate_cost(data)
            next_images.append((next_available, name, data, cost))

        next_images.sort(key=lambda x: x[0])

        lines.append("[bold cyan]Next 5 Available Images:[/bold cyan]\n")
        for i, (next_time, name, data, cost) in enumerate(next_images[:5]):
            time_str = self.format_time_delta(next_time)
            weather_icon = "cloud" if not data["weather_independent"] else "satellite"

            cost_val = 0 if cost == "FREE" else float(cost.replace("$", "").replace(",", ""))
            if cost == "FREE":
                cost_color = "green"
            elif cost_val < 500:
                cost_color = "yellow"
            else:
                cost_color = "red"

            lines.append(
                f"{i + 1}. [bold]{name}[/bold] - {time_str}\n"
                f"   {weather_icon} {data['type']} * {data['resolution_m']}m * "
                f"[{cost_color}]{cost}[/{cost_color}]"
            )

        return Panel("\n".join(lines), title="Upcoming", border_style="green")

    def create_recommendations_panel(self) -> Panel:
        """Create recommendations panel based on current weather."""
        weather = self.get_current_weather()

        if weather is None:
            # No weather API configured
            lines = [
                "[bold cyan]Recommendations:[/bold cyan]",
                "[yellow]No weather API configured[/yellow]",
                "   Run [cyan]satellite-monitor setup[/cyan] to configure weather APIs",
                "   for weather-aware satellite recommendations.\n",
                "[bold]Without weather data:[/bold]",
                "   SAR satellites (Sentinel-1, ICEYE, Capella) always work",
                "   Optical satellites depend on cloud cover - check local weather\n",
                "[bold]Quick Decision Guide:[/bold]",
                "Best FREE option: Sentinel-1 (SAR) or Sentinel-2 (optical if clear)",
                "Best quality: ICEYE (0.25m SAR) or WorldView-3 (0.31m optical if clear)",
                "Fastest delivery: BlackSky (1-2h, optical - requires clear weather)"
            ]
            return Panel("\n".join(lines), title="Recommendations", border_style="yellow")

        cloud_cover = weather.current_cloud_cover
        is_day = weather.is_daylight

        lines = [
            f"[bold cyan]Weather-Based Recommendations:[/bold cyan]",
            f"Current cloud cover: {cloud_cover}% ({weather.current_conditions})",
            f"Visibility: {weather.current_visibility_km:.1f} km | "
            f"{'Daylight' if is_day else 'Night'}\n",
        ]

        # Weather-specific recommendations
        if cloud_cover < 30 and is_day:
            lines.extend([
                "[bold green]EXCELLENT CONDITIONS for optical satellites![/bold green]",
                "   All optical satellites will work well",
                "   Use FREE Sentinel-2 for 10m resolution",
                "   Use PlanetScope ($250) for 3m resolution",
                "   Use WorldView-3 ($2,500) for 0.31m resolution\n"
            ])
        elif cloud_cover < 60 and is_day:
            lines.extend([
                "[bold yellow]MODERATE CONDITIONS for optical satellites[/bold yellow]",
                "   Some optical satellites may have reduced quality",
                "   Sentinel-2 (FREE) - May work with gaps",
                "   Consider SkySat ($1,000) for better penetration",
                "   SAR satellites guaranteed to work\n"
            ])
        else:
            conditions = "cloudy" if cloud_cover >= 60 else "night"
            lines.extend([
                f"[bold red]POOR CONDITIONS for optical ({conditions})[/bold red]",
                "   Optical satellites will not work well",
                "   MUST use SAR satellites:",
                "   Sentinel-1 (FREE) - 5m SAR",
                "   Capella ($8,000) - 0.5m SAR",
                "   ICEYE ($10,000) - 0.25m SAR\n"
            ])

        # General recommendations
        best_free = "Sentinel-2 (optical)" if cloud_cover < 30 and is_day else "Sentinel-1 (SAR)"
        best_quality = "WorldView-3 (0.31m optical)" if cloud_cover < 20 and is_day else "ICEYE (0.25m SAR)"

        lines.extend([
            "[bold]Quick Decision Guide:[/bold]",
            f"Best FREE option: {best_free}",
            f"Best quality: {best_quality}",
            f"Fastest delivery: BlackSky (1-2h) {'if clear' if cloud_cover < 30 else '(too cloudy)'}"
        ])

        return Panel("\n".join(lines), title="Smart Recommendations", border_style="cyan")

    def run(self, watch: bool = False) -> None:
        """Run the checker and display results.

        Args:
            watch: If True, continuously update display every minute
        """
        if watch:
            with Live(console=self.console, refresh_per_second=1) as live:
                while True:
                    self._display_all()
                    time.sleep(60)
                    self.refresh_weather()
        else:
            self._display_all()

    def _display_all(self) -> None:
        """Display all panels."""
        self.console.print(self.create_summary_table())
        self.console.print()
        self.console.print(self.create_next_available_panel())
        self.console.print()
        self.console.print(self.create_recommendations_panel())

    def to_json(self) -> str:
        """Export satellite data as JSON."""
        output = {
            "location": {
                "name": self.location.name,
                "latitude": self.location.latitude,
                "longitude": self.location.longitude,
            },
            "area_sqkm": self.area_sqkm,
            "satellites": {}
        }

        for name, data in self.satellites.items():
            last_available, next_pass, next_available = self.calculate_times(data)
            output["satellites"][name] = {
                "provider": data["provider"],
                "type": data["type"],
                "resolution_m": data["resolution_m"],
                "last_image_available": last_available.isoformat(),
                "next_pass": next_pass.isoformat(),
                "next_image_available": next_available.isoformat(),
                "cost_usd": data["cost_per_sqkm"] * self.area_sqkm,
                "weather_independent": data["weather_independent"]
            }

        return json.dumps(output, indent=2)


# Backwards compatibility alias
QuickSatelliteChecker = SatelliteChecker
