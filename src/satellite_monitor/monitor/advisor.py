"""Smart satellite advisor with weather-aware recommendations."""

from __future__ import annotations

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from ..core.location import Location
from ..weather.models import SatelliteRecommendation, WeatherData
from ..weather.service import WeatherService


# Satellite database with weather sensitivity information
ADVISOR_SATELLITES = {
    # SAR satellites (weather-independent)
    "Sentinel-1": {
        "provider": "ESA",
        "type": "SAR",
        "resolution_m": 5,
        "revisit_hours": 144,
        "cost_per_sqkm": 0,
        "weather_independent": True,
        "min_cloud_ok": 100,
        "requires_daylight": False,
        "data_latency_hours": 3
    },
    "ICEYE": {
        "provider": "ICEYE",
        "type": "SAR",
        "resolution_m": 0.25,
        "revisit_hours": 24,
        "cost_per_sqkm": 100,
        "weather_independent": True,
        "min_cloud_ok": 100,
        "requires_daylight": False,
        "data_latency_hours": 2
    },
    "Capella": {
        "provider": "Capella Space",
        "type": "SAR",
        "resolution_m": 0.5,
        "revisit_hours": 24,
        "cost_per_sqkm": 80,
        "weather_independent": True,
        "min_cloud_ok": 100,
        "requires_daylight": False,
        "data_latency_hours": 1
    },
    # Optical satellites (weather-dependent)
    "Sentinel-2": {
        "provider": "ESA",
        "type": "Optical",
        "resolution_m": 10,
        "revisit_hours": 120,
        "cost_per_sqkm": 0,
        "weather_independent": False,
        "min_cloud_ok": 30,
        "requires_daylight": True,
        "data_latency_hours": 3
    },
    "PlanetScope": {
        "provider": "Planet",
        "type": "Optical",
        "resolution_m": 3,
        "revisit_hours": 24,
        "cost_per_sqkm": 2.5,
        "weather_independent": False,
        "min_cloud_ok": 20,
        "requires_daylight": True,
        "data_latency_hours": 2
    },
    "SkySat": {
        "provider": "Planet",
        "type": "Optical",
        "resolution_m": 0.5,
        "revisit_hours": 24,
        "cost_per_sqkm": 10,
        "weather_independent": False,
        "min_cloud_ok": 15,
        "requires_daylight": True,
        "data_latency_hours": 3
    },
    "WorldView-3": {
        "provider": "Maxar",
        "type": "Optical",
        "resolution_m": 0.31,
        "revisit_hours": 24,
        "cost_per_sqkm": 25,
        "weather_independent": False,
        "min_cloud_ok": 10,
        "requires_daylight": True,
        "data_latency_hours": 12
    },
    "Pleiades-Neo": {
        "provider": "Airbus",
        "type": "Optical",
        "resolution_m": 0.3,
        "revisit_hours": 24,
        "cost_per_sqkm": 30,
        "weather_independent": False,
        "min_cloud_ok": 10,
        "requires_daylight": True,
        "data_latency_hours": 6
    },
    "BlackSky": {
        "provider": "BlackSky",
        "type": "Optical",
        "resolution_m": 1,
        "revisit_hours": 24,
        "cost_per_sqkm": 4.5,
        "weather_independent": False,
        "min_cloud_ok": 25,
        "requires_daylight": True,
        "data_latency_hours": 1
    }
}


class SmartSatelliteAdvisor:
    """Intelligent satellite recommendation based on weather and requirements.

    Analyzes current weather conditions and user requirements to provide
    scored recommendations for the best satellite options.
    """

    def __init__(
        self,
        location: Location | None = None,
        area_sqkm: float = 100
    ):
        """Initialize the advisor.

        Args:
            location: Target location. Defaults to Brussels.
            area_sqkm: Coverage area in square kilometers.
        """
        self.location = location or Location.brussels()
        self.area_sqkm = area_sqkm
        self.console = Console()
        self.weather_service = WeatherService(location=self.location)
        self.satellites = ADVISOR_SATELLITES.copy()

    def get_recommendations(
        self,
        weather: WeatherData,
        max_budget: float | None = None,
        min_resolution: float | None = None,
        urgency_hours: float | None = None
    ) -> list[SatelliteRecommendation]:
        """Get smart satellite recommendations based on current weather.

        Args:
            weather: Current weather data
            max_budget: Maximum budget per image in USD
            min_resolution: Required resolution in meters (lower is better)
            urgency_hours: Required delivery time in hours

        Returns:
            List of recommendations sorted by score (highest first)
        """
        recommendations = []

        for sat_name, sat_info in self.satellites.items():
            score = 100.0
            reasons = []
            weather_suitable = True

            # Calculate cost
            cost = sat_info["cost_per_sqkm"] * self.area_sqkm
            cost_str = "FREE" if cost == 0 else f"${cost:,.0f}"

            # Weather suitability check
            if not sat_info["weather_independent"]:
                if weather.current_cloud_cover > sat_info["min_cloud_ok"]:
                    weather_suitable = False
                    penalty = (weather.current_cloud_cover - sat_info["min_cloud_ok"]) * 2
                    score -= penalty
                    reasons.append(
                        f"Too cloudy ({weather.current_cloud_cover:.0f}% > "
                        f"{sat_info['min_cloud_ok']}% threshold)"
                    )
                else:
                    score += 20
                    reasons.append(
                        f"Good cloud conditions ({weather.current_cloud_cover:.0f}%)"
                    )

                if sat_info["requires_daylight"] and not weather.is_daylight:
                    weather_suitable = False
                    score -= 50
                    reasons.append("Requires daylight (currently night)")
            else:
                score += 30  # Bonus for weather independence
                reasons.append("All-weather capability (SAR)")
                weather_suitable = True

            # Budget check
            if max_budget is not None and cost > max_budget:
                score -= 20
                reasons.append(f"Over budget (${cost:.0f} > ${max_budget:.0f})")
            elif cost == 0:
                score += 15
                reasons.append("Free data")

            # Resolution check
            if min_resolution is not None and sat_info["resolution_m"] > min_resolution:
                score -= 15
                reasons.append(
                    f"Lower resolution than required "
                    f"({sat_info['resolution_m']}m > {min_resolution}m)"
                )

            # Urgency check
            eta = sat_info["revisit_hours"] + sat_info["data_latency_hours"]
            if urgency_hours is not None and eta > urgency_hours:
                score -= 25
                reasons.append(f"Too slow (ETA {eta}h > {urgency_hours}h required)")
            elif eta <= 24:
                score += 10
                reasons.append(f"Fast delivery ({eta}h)")

            # Determine quality estimate
            if score >= 80:
                quality = "Excellent"
            elif score >= 60:
                quality = "Good"
            elif score >= 40:
                quality = "Fair"
            else:
                quality = "Poor"

            recommendations.append(SatelliteRecommendation(
                satellite_name=sat_name,
                provider=sat_info["provider"],
                score=max(0, min(100, score)),
                reasons=reasons,
                estimated_quality=quality,
                cost=cost_str,
                eta_hours=eta,
                weather_suitable=weather_suitable
            ))

        # Sort by score descending
        recommendations.sort(key=lambda x: x.score, reverse=True)
        return recommendations

    def create_weather_panel(self, weather: WeatherData) -> Panel:
        """Create weather status panel."""
        cloud_cover = weather.current_cloud_cover

        if cloud_cover < 20:
            cloud_indicator = "Clear"
        elif cloud_cover < 40:
            cloud_indicator = "Partly cloudy"
        elif cloud_cover < 60:
            cloud_indicator = "Mostly cloudy"
        elif cloud_cover < 80:
            cloud_indicator = "Cloudy"
        else:
            cloud_indicator = "Overcast"

        daylight_status = "Daylight" if weather.is_daylight else "Night"

        # Forecast summary
        forecast_lines = []
        for f in weather.forecast_24h[:3]:
            time_str = f["time"].strftime("%H:%M")
            clouds = f["clouds"]
            forecast_lines.append(f"{time_str}: {clouds}%")

        content = f"""
[bold cyan]Current Conditions in {self.location.name}[/bold cyan]

Cloud Cover: [bold]{cloud_cover:.0f}%[/bold] ({cloud_indicator})
Visibility: {weather.current_visibility_km:.1f} km
Conditions: {weather.current_conditions}
{daylight_status} (Sunrise: {weather.sunrise.strftime('%H:%M')}, Sunset: {weather.sunset.strftime('%H:%M')})

[bold]Next 9 Hours:[/bold]
{chr(10).join(forecast_lines)}

[dim]Last updated: {weather.last_updated.strftime('%H:%M:%S UTC')}[/dim]
"""

        # Color based on conditions
        if cloud_cover < 30:
            border_style = "green"
        elif cloud_cover < 70:
            border_style = "yellow"
        else:
            border_style = "red"

        return Panel(content.strip(), title="Weather Status", border_style=border_style)

    def create_recommendations_table(
        self,
        recommendations: list[SatelliteRecommendation]
    ) -> Table:
        """Create recommendations table."""
        table = Table(
            title="Satellite Recommendations (Weather-Aware)",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan"
        )

        table.add_column("Rank", justify="center", width=6)
        table.add_column("Satellite", width=15)
        table.add_column("Provider", width=12)
        table.add_column("Score", justify="center", width=8)
        table.add_column("Quality", width=12)
        table.add_column("Cost", justify="right", width=10)
        table.add_column("ETA", justify="center", width=8)
        table.add_column("Key Factors", width=40)

        for i, rec in enumerate(recommendations[:10], 1):
            # Color code by score
            if rec.score >= 80:
                score_color = "green"
                rank_display = "#1" if i == 1 else f"#{i}"
            elif rec.score >= 60:
                score_color = "yellow"
                rank_display = f"#{i}"
            else:
                score_color = "red"
                rank_display = f"#{i}"

            # Cost coloring
            if rec.cost == "FREE":
                cost_display = "[green]FREE[/green]"
            elif rec.get_cost_value() > 1000:
                cost_display = f"[red]{rec.cost}[/red]"
            else:
                cost_display = f"[yellow]{rec.cost}[/yellow]"

            # Quality coloring
            quality_colors = {
                "Excellent": "green",
                "Good": "cyan",
                "Fair": "yellow",
                "Poor": "red"
            }
            color = quality_colors.get(rec.estimated_quality, "white")
            quality_display = f"[{color}]{rec.estimated_quality}[/{color}]"

            # Top reasons
            key_factors = "\n".join(rec.reasons[:2])

            table.add_row(
                rank_display,
                rec.satellite_name,
                rec.provider,
                f"[{score_color}]{rec.score:.0f}[/{score_color}]",
                quality_display,
                cost_display,
                f"{rec.eta_hours:.0f}h",
                key_factors
            )

        return table

    def create_optimal_choice_panel(
        self,
        weather: WeatherData,
        recommendations: list[SatelliteRecommendation]
    ) -> Panel:
        """Create panel with optimal choices for different scenarios."""
        # Find best options for different scenarios
        suitable = [r for r in recommendations if r.weather_suitable]

        best_free = next((r for r in suitable if r.is_free), None)
        best_budget = next(
            (r for r in suitable if not r.is_free and r.get_cost_value() < 500),
            None
        )
        best_quality = suitable[0] if suitable else None
        best_urgent = min(suitable, key=lambda x: x.eta_hours, default=None)
        best_any_weather = next(
            (r for r in recommendations if "SAR" in " ".join(r.reasons)),
            None
        )

        lines = ["[bold cyan]Optimal Choices Based on Current Weather:[/bold cyan]\n"]

        if weather.current_cloud_cover < 30:
            lines.append("[green]EXCELLENT CONDITIONS for optical satellites![/green]")
            lines.append("   Recommendation: Use cheap optical satellites today\n")
        elif weather.current_cloud_cover < 70:
            lines.append("[yellow]MODERATE CONDITIONS for optical satellites[/yellow]")
            lines.append("   Recommendation: High-res optical or SAR for guaranteed results\n")
        else:
            lines.append("[red]POOR CONDITIONS for optical satellites[/red]")
            lines.append("   Recommendation: Use SAR satellites only\n")

        if best_free:
            lines.append(f"[bold]Best Free Option:[/bold] {best_free.satellite_name}")
            lines.append(f"   Quality: {best_free.estimated_quality}, ETA: {best_free.eta_hours:.0f}h")

        if best_budget:
            lines.append(f"\n[bold]Best Budget Option:[/bold] {best_budget.satellite_name}")
            lines.append(f"   Cost: {best_budget.cost}, Quality: {best_budget.estimated_quality}")

        if best_urgent:
            lines.append(f"\n[bold]Fastest Option:[/bold] {best_urgent.satellite_name}")
            lines.append(f"   ETA: {best_urgent.eta_hours:.0f}h, Cost: {best_urgent.cost}")

        if best_any_weather:
            lines.append(f"\n[bold]Best All-Weather:[/bold] {best_any_weather.satellite_name}")
            lines.append(f"   SAR imaging works through clouds, Cost: {best_any_weather.cost}")

        # Add forecast-based advice
        lines.append("\n[bold]Planning Ahead:[/bold]")

        if len(weather.forecast_24h) > 0:
            future_clouds = [f["clouds"] for f in weather.forecast_24h[:3]]
            avg_future = sum(future_clouds) / len(future_clouds)

            if avg_future < weather.current_cloud_cover - 20:
                lines.append("   Weather improving: Consider waiting for optical satellites")
            elif avg_future > weather.current_cloud_cover + 20:
                lines.append("   Weather worsening: Book SAR satellites now")
            else:
                lines.append("   Weather stable: Current recommendations remain valid")

        return Panel("\n".join(lines), title="Smart Recommendations", border_style="cyan")

    def _create_no_weather_panel(self) -> Panel:
        """Create panel when no weather API is configured."""
        content = """[bold yellow]No Weather API Configured[/bold yellow]

Weather-aware recommendations require a weather API.
Run [cyan]satellite-monitor setup[/cyan] to configure.

[bold]Without weather data:[/bold]
   SAR satellites always work regardless of weather
   Optical satellites require clear skies and daylight

[bold]Recommended SAR options:[/bold]
   Sentinel-1 (FREE) - 5m resolution
   Capella ($8,000) - 0.5m resolution
   ICEYE ($10,000) - 0.25m resolution"""
        return Panel(content, title="Weather Status", border_style="yellow")

    def run(
        self,
        max_budget: float | None = None,
        min_resolution: float | None = None,
        urgency_hours: float | None = None
    ) -> None:
        """Run the advisor and display results."""
        self.console.clear()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
            transient=True
        ) as progress:
            task = progress.add_task("Fetching weather data...", total=None)
            weather = self.weather_service.get_weather()
            progress.update(task, completed=100)

        # Handle no weather API configured
        if weather is None:
            self.console.print("\n")
            self.console.print(self._create_no_weather_panel())
            self.console.print("\n")
            self.console.print(
                "[yellow]Run [cyan]satellite-monitor setup[/cyan] to configure "
                "weather APIs for full recommendations.[/yellow]"
            )
            return

        # Get recommendations with weather data
        recommendations = self.get_recommendations(
            weather,
            max_budget=max_budget,
            min_resolution=min_resolution,
            urgency_hours=urgency_hours
        )

        # Display results
        self.console.print("\n")
        self.console.print(self.create_weather_panel(weather))
        self.console.print("\n")
        self.console.print(self.create_recommendations_table(recommendations))
        self.console.print("\n")
        self.console.print(self.create_optimal_choice_panel(weather, recommendations))
