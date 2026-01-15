"""Command-line interface for satellite-monitor."""

from __future__ import annotations

import click

from ..core.location import Area, Location, resolve_location


@click.group()
@click.option(
    '--lat',
    type=float,
    help='Latitude of target location'
)
@click.option(
    '--lon',
    type=float,
    help='Longitude of target location'
)
@click.option(
    '--location', '-l',
    type=str,
    default=None,
    help='Named location (e.g., "London", "Paris", "Tokyo"). Supports 60+ presets or any location via geocoding.'
)
@click.option(
    '--area-km',
    type=float,
    default=100,
    help='Coverage area in square kilometers (default: 100)'
)
@click.version_option()
@click.pass_context
def cli(
    ctx: click.Context,
    lat: float | None,
    lon: float | None,
    location: str | None,
    area_km: float
) -> None:
    """Satellite monitoring and recommendation tool.

    Monitor satellite availability, get weather-aware recommendations,
    and download Sentinel imagery for any location.

    Examples:

        satellite-monitor check

        satellite-monitor --location London check

        satellite-monitor -l "New York" recommend

        satellite-monitor --lat 48.8566 --lon 2.3522 check

        satellite-monitor download --days 14 --dry-run
    """
    ctx.ensure_object(dict)

    # Determine location (priority: lat/lon > --location > default Brussels)
    if lat is not None and lon is not None:
        # Explicit coordinates provided
        name = location if location else "Custom"
        ctx.obj['location'] = Location(
            name=name,
            latitude=lat,
            longitude=lon
        )
        ctx.obj['area'] = Area.from_center(
            name=name,
            latitude=lat,
            longitude=lon,
            radius_km=(area_km ** 0.5) / 2  # Approximate square area
        )
    elif location:
        # Named location provided - resolve it
        resolved = resolve_location(location)
        if resolved is None:
            raise click.ClickException(
                f"Could not find location '{location}'. "
                "Try a different name or use --lat/--lon coordinates."
            )
        ctx.obj['location'] = resolved
        ctx.obj['area'] = Area.from_location(resolved, radius_km=(area_km ** 0.5) / 2)
    else:
        # Default to Brussels
        ctx.obj['location'] = Location.brussels()
        ctx.obj['area'] = Area.brussels()

    ctx.obj['area_sqkm'] = area_km


@cli.command()
@click.option(
    '--watch', '-w',
    is_flag=True,
    help='Enable live update mode (refresh every minute)'
)
@click.option(
    '--json', '-j', 'output_json',
    is_flag=True,
    help='Output as JSON for automation'
)
@click.pass_context
def check(ctx: click.Context, watch: bool, output_json: bool) -> None:
    """Check current satellite availability.

    Shows satellite pass times, costs, weather suitability,
    and smart recommendations based on current conditions.
    """
    from ..monitor.checker import SatelliteChecker

    location = ctx.obj['location']
    area_sqkm = ctx.obj['area_sqkm']

    checker = SatelliteChecker(location=location, area_sqkm=area_sqkm)

    if output_json:
        click.echo(checker.to_json())
    else:
        checker.run(watch=watch)


@cli.command()
@click.option(
    '--budget',
    type=float,
    help='Maximum budget per image in USD'
)
@click.option(
    '--resolution',
    type=float,
    help='Required resolution in meters'
)
@click.option(
    '--urgent',
    type=float,
    help='Required delivery time in hours'
)
@click.option(
    '--json', '-j', 'output_json',
    is_flag=True,
    help='Output as JSON for automation'
)
@click.pass_context
def recommend(
    ctx: click.Context,
    budget: float | None,
    resolution: float | None,
    urgent: float | None,
    output_json: bool
) -> None:
    """Get weather-aware satellite recommendations.

    Analyzes current weather conditions and provides scored
    recommendations based on your requirements.
    """
    import json

    from ..monitor.advisor import SmartSatelliteAdvisor

    location = ctx.obj['location']
    area_sqkm = ctx.obj['area_sqkm']

    advisor = SmartSatelliteAdvisor(location=location, area_sqkm=area_sqkm)

    if output_json:
        weather = advisor.weather_service.get_weather()
        recommendations = advisor.get_recommendations(
            weather,
            max_budget=budget,
            min_resolution=resolution,
            urgency_hours=urgent
        )

        output = {
            "location": {
                "name": location.name,
                "latitude": location.latitude,
                "longitude": location.longitude,
            },
            "weather": {
                "cloud_cover_percent": weather.current_cloud_cover,
                "visibility_km": weather.current_visibility_km,
                "conditions": weather.current_conditions,
                "is_daylight": weather.is_daylight
            },
            "recommendations": [
                {
                    "satellite": r.satellite_name,
                    "provider": r.provider,
                    "score": r.score,
                    "quality": r.estimated_quality,
                    "cost_usd": r.get_cost_value(),
                    "eta_hours": r.eta_hours,
                    "weather_suitable": r.weather_suitable,
                    "reasons": r.reasons
                }
                for r in recommendations[:5]
            ],
            "best_choice": recommendations[0].satellite_name if recommendations else None
        }
        click.echo(json.dumps(output, indent=2))
    else:
        advisor.run(
            max_budget=budget,
            min_resolution=resolution,
            urgency_hours=urgent
        )


@cli.command()
@click.option(
    '--days',
    default=30,
    help='Days back to search (default: 30)'
)
@click.option(
    '--cloud-max',
    default=20,
    help='Maximum cloud coverage percentage (default: 20)'
)
@click.option(
    '--max-products',
    default=3,
    help='Maximum products per satellite (default: 3)'
)
@click.option(
    '--output-dir', '-o',
    type=click.Path(),
    help='Download directory'
)
@click.option(
    '--dry-run',
    is_flag=True,
    help='Search only, do not download'
)
@click.pass_context
def download(
    ctx: click.Context,
    days: int,
    cloud_max: int,
    max_products: int,
    output_dir: str | None,
    dry_run: bool
) -> None:
    """Download Sentinel satellite data.

    Downloads Sentinel-1 (SAR) and Sentinel-2 (optical) imagery
    from ESA Copernicus Hub.

    Requires credentials:
        export COPERNICUS_USERNAME='your_username'
        export COPERNICUS_PASSWORD='your_password'

    Register at: https://scihub.copernicus.eu/dhus/#/self-registration
    """
    from pathlib import Path

    try:
        from ..download.quick import download_latest_sentinel
    except ImportError:
        click.echo(
            "Error: Download feature requires sentinel dependencies.\n"
            "Install with: pip install satellite-monitor[sentinel]",
            err=True
        )
        ctx.exit(1)

    area = ctx.obj['area']

    try:
        result = download_latest_sentinel(
            area=area,
            output_dir=Path(output_dir) if output_dir else None,
            days_back=days,
            max_cloud_coverage=cloud_max,
            max_products=max_products,
            dry_run=dry_run
        )

        if result["success"]:
            click.echo("\nDownload Summary")
            click.echo("=" * 40)
            click.echo(f"Area: {result['area']}")
            click.echo(f"Sentinel-1 products: {result['sentinel1_count']}")
            click.echo(f"Sentinel-2 products: {result['sentinel2_count']}")
            click.echo(f"Output directory: {result['output_dir']}")
            if dry_run:
                click.echo("\n(Dry run - no files downloaded)")
        else:
            click.echo(f"Error: {result.get('error', 'Unknown error')}", err=True)
            ctx.exit(1)

    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        ctx.exit(1)


@cli.command()
def setup() -> None:
    """Configure weather API keys.

    Interactive wizard to set up weather data sources
    for accurate cloud cover information.
    """
    from ..weather.setup import run_setup_wizard

    run_setup_wizard()


@cli.command()
def locations() -> None:
    """List available preset locations.

    Shows all built-in location presets that can be used with --location.
    Any other location name will be geocoded via OpenStreetMap.
    """
    from ..core.location import PRESET_LOCATIONS

    click.echo("Available preset locations:")
    click.echo("=" * 40)

    # Group by region
    regions = {
        "Europe": ["brussels", "london", "paris", "amsterdam", "berlin", "rome",
                   "madrid", "vienna", "prague", "stockholm", "oslo", "copenhagen",
                   "helsinki", "dublin", "lisbon", "zurich", "geneva", "munich",
                   "barcelona", "milan"],
        "North America": ["new york", "los angeles", "san francisco", "chicago",
                          "washington dc", "boston", "seattle", "denver", "toronto",
                          "vancouver", "montreal", "mexico city"],
        "Asia": ["tokyo", "beijing", "shanghai", "hong kong", "singapore", "seoul",
                 "mumbai", "delhi", "bangalore", "bangkok", "dubai", "tel aviv"],
        "Oceania": ["sydney", "melbourne", "auckland", "perth"],
        "South America": ["sao paulo", "rio de janeiro", "buenos aires", "santiago",
                          "bogota", "lima"],
        "Africa": ["cairo", "cape town", "johannesburg", "nairobi", "lagos", "casablanca"],
    }

    for region, cities in regions.items():
        click.echo(f"\n{region}:")
        # Format cities in columns
        row = []
        for city in cities:
            if city in PRESET_LOCATIONS:
                row.append(city.title())
                if len(row) == 4:
                    click.echo("  " + ", ".join(row))
                    row = []
        if row:
            click.echo("  " + ", ".join(row))

    click.echo("\n" + "=" * 40)
    click.echo("Usage: satellite-monitor --location London check")
    click.echo("       satellite-monitor -l 'New York' recommend")
    click.echo("\nAny other location will be geocoded via OpenStreetMap.")


@cli.command()
@click.pass_context
def demo(ctx: click.Context) -> None:
    """Run an interactive demonstration.

    Shows the main features of the satellite monitoring system
    with your current location settings.
    """
    from rich.console import Console
    from rich.panel import Panel

    from ..monitor.checker import SatelliteChecker

    console = Console()
    location = ctx.obj['location']
    area_sqkm = ctx.obj['area_sqkm']

    console.print(Panel.fit(
        f"Satellite Monitor Demo - {location.name}",
        style="bold cyan"
    ))
    console.print()

    console.print("[bold]1. Checking satellite availability...[/bold]")
    console.print()

    checker = SatelliteChecker(location=location, area_sqkm=area_sqkm)
    checker.run()

    console.print()
    console.print(Panel(
        "Demo complete! Try these commands:\n\n"
        "  satellite-monitor check --watch    # Live updates\n"
        "  satellite-monitor recommend        # Smart recommendations\n"
        "  satellite-monitor setup            # Configure weather APIs\n"
        "  satellite-monitor download --dry-run  # Search Sentinel data",
        title="Next Steps",
        border_style="green"
    ))


def main() -> None:
    """Main entry point for CLI."""
    cli(obj={})


if __name__ == "__main__":
    main()
