"""
Satellite Monitor - Multi-provider satellite imagery monitoring tool.

A weather-aware satellite monitoring system that tracks both public and
commercial satellites, providing smart recommendations based on current
conditions and user requirements.

Basic Usage:
    from satellite_monitor import Location, SatelliteChecker, resolve_location

    # Use default location (Brussels)
    checker = SatelliteChecker()
    checker.run()

    # Resolve named location (60+ presets, or any location via geocoding)
    london = resolve_location("London")
    checker = SatelliteChecker(location=london)
    checker.run()

    # Custom location with coordinates
    paris = Location(name="Paris", latitude=48.8566, longitude=2.3522)
    checker = SatelliteChecker(location=paris)
    checker.run()

CLI Usage:
    satellite-monitor check
    satellite-monitor --location London check
    satellite-monitor -l "New York" recommend
    satellite-monitor setup
"""

__version__ = "1.0.0"

# Core types
from satellite_monitor.core.location import (
    Area,
    Location,
    PRESET_LOCATIONS,
    resolve_location,
)
from satellite_monitor.core.passes import SatellitePass
from satellite_monitor.core.providers import SatelliteProvider
from satellite_monitor.core.satellites import SATELLITE_CATALOG, SatelliteSpecs

# Monitor classes
from satellite_monitor.monitor.advisor import SmartSatelliteAdvisor
from satellite_monitor.monitor.checker import QuickSatelliteChecker, SatelliteChecker
from satellite_monitor.monitor.monitor import SatelliteMonitor

# Weather
from satellite_monitor.weather.models import SatelliteRecommendation, WeatherData
from satellite_monitor.weather.service import WeatherService

# Download (optional - may raise ImportError if dependencies not installed)
# Use lazy import pattern in user code:
#   from satellite_monitor.download import SentinelDownloader

__all__ = [
    # Version
    "__version__",
    # Core
    "Location",
    "Area",
    "resolve_location",
    "PRESET_LOCATIONS",
    "SatelliteProvider",
    "SatelliteSpecs",
    "SatellitePass",
    "SATELLITE_CATALOG",
    # Monitor
    "SatelliteChecker",
    "QuickSatelliteChecker",  # Backwards compatibility alias
    "SatelliteMonitor",
    "SmartSatelliteAdvisor",
    # Weather
    "WeatherData",
    "SatelliteRecommendation",
    "WeatherService",
]
