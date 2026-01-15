"""Weather integration for satellite monitoring."""

from .models import SatelliteRecommendation, WeatherData
from .service import WeatherService
from .setup import run_setup_wizard, test_openweathermap_api, test_weatherapi_key

__all__ = [
    "WeatherData",
    "SatelliteRecommendation",
    "WeatherService",
    "run_setup_wizard",
    "test_openweathermap_api",
    "test_weatherapi_key",
]
