"""Weather service for fetching cloud cover and conditions."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
import requests

from ..core.location import Location
from .models import WeatherData


class WeatherService:
    """Service to get weather and cloud cover data for satellite planning.

    Supports multiple weather API backends:
    - OpenWeatherMap (free tier: 1,000 calls/day)
    - WeatherAPI.com (free tier: 1M calls/month)

    Returns None if no API keys are configured.
    """

    def __init__(self, location: Location | None = None):
        """Initialize the weather service.

        Args:
            location: Target location for weather data. Defaults to Brussels.
        """
        self.location = location or Location.brussels()

        # API configuration from environment
        self.apis = {
            "openweathermap": {
                "url": "https://api.openweathermap.org/data/2.5/weather",
                "forecast_url": "https://api.openweathermap.org/data/2.5/forecast",
                "key": os.getenv("OPENWEATHER_API_KEY", "")
            },
            "weatherapi": {
                "url": "https://api.weatherapi.com/v1/current.json",
                "forecast_url": "https://api.weatherapi.com/v1/forecast.json",
                "key": os.getenv("WEATHERAPI_KEY", "")
            },
        }

    def get_weather(self) -> WeatherData | None:
        """Get current weather and cloud cover.

        Tries APIs in order, returns None if no API keys configured.

        Returns:
            WeatherData or None if no API configured or retrieval failed
        """
        # Try OpenWeatherMap first
        weather_data = self._get_openweathermap()
        if weather_data:
            return weather_data

        # Fallback to WeatherAPI
        weather_data = self._get_weatherapi()
        if weather_data:
            return weather_data

        # No API keys configured
        return None

    def _get_openweathermap(self) -> WeatherData | None:
        """Get weather from OpenWeatherMap API."""
        if not self.apis["openweathermap"]["key"]:
            return None

        try:
            # Current weather
            response = requests.get(
                self.apis["openweathermap"]["url"],
                params={
                    "lat": self.location.latitude,
                    "lon": self.location.longitude,
                    "appid": self.apis["openweathermap"]["key"],
                    "units": "metric"
                },
                timeout=5
            )
            if response.status_code != 200:
                return None

            current = response.json()

            # Forecast
            forecast_response = requests.get(
                self.apis["openweathermap"]["forecast_url"],
                params={
                    "lat": self.location.latitude,
                    "lon": self.location.longitude,
                    "appid": self.apis["openweathermap"]["key"],
                    "units": "metric",
                    "cnt": 24
                },
                timeout=5
            )
            forecast = (
                forecast_response.json()
                if forecast_response.status_code == 200
                else {"list": []}
            )

            now = datetime.now(timezone.utc)
            sunrise = datetime.fromtimestamp(current["sys"]["sunrise"], timezone.utc)
            sunset = datetime.fromtimestamp(current["sys"]["sunset"], timezone.utc)

            return WeatherData(
                current_cloud_cover=current["clouds"]["all"],
                current_visibility_km=current.get("visibility", 10000) / 1000,
                current_conditions=current["weather"][0]["description"],
                forecast_24h=[
                    {
                        "time": datetime.fromtimestamp(f["dt"], timezone.utc),
                        "clouds": f["clouds"]["all"],
                        "conditions": f["weather"][0]["main"]
                    }
                    for f in forecast.get("list", [])[:8]
                ],
                forecast_daily=self._aggregate_daily_forecast(forecast.get("list", [])),
                last_updated=now,
                sunrise=sunrise,
                sunset=sunset,
                is_daylight=sunrise < now < sunset
            )

        except Exception:
            return None

    def _get_weatherapi(self) -> WeatherData | None:
        """Get weather from WeatherAPI.com."""
        if not self.apis["weatherapi"]["key"]:
            return None

        try:
            response = requests.get(
                self.apis["weatherapi"]["forecast_url"],
                params={
                    "key": self.apis["weatherapi"]["key"],
                    "q": f"{self.location.latitude},{self.location.longitude}",
                    "days": 3,
                    "aqi": "no"
                },
                timeout=5
            )
            if response.status_code != 200:
                return None

            data = response.json()
            current = data["current"]
            location_data = data["location"]

            now = datetime.now(timezone.utc)

            # Parse astronomy data
            astro = data["forecast"]["forecastday"][0]["astro"]
            date_str = location_data['localtime'][:10]
            sunrise = datetime.strptime(
                f"{date_str} {astro['sunrise']}", "%Y-%m-%d %I:%M %p"
            )
            sunset = datetime.strptime(
                f"{date_str} {astro['sunset']}", "%Y-%m-%d %I:%M %p"
            )

            return WeatherData(
                current_cloud_cover=current["cloud"],
                current_visibility_km=current["vis_km"],
                current_conditions=current["condition"]["text"],
                forecast_24h=[
                    {
                        "time": datetime.fromtimestamp(h["time_epoch"], timezone.utc),
                        "clouds": h["cloud"],
                        "conditions": h["condition"]["text"]
                    }
                    for h in data["forecast"]["forecastday"][0]["hour"]
                ],
                forecast_daily=[
                    {
                        "date": d["date"],
                        "avg_clouds": d["day"].get("cloud", 50),
                        "conditions": d["day"]["condition"]["text"]
                    }
                    for d in data["forecast"]["forecastday"]
                ],
                last_updated=now,
                sunrise=sunrise.replace(tzinfo=timezone.utc),
                sunset=sunset.replace(tzinfo=timezone.utc),
                is_daylight=current["is_day"] == 1
            )

        except Exception:
            return None

    def _aggregate_daily_forecast(self, forecast_list: list) -> list[dict]:
        """Aggregate hourly forecast into daily summaries."""
        daily: dict[str, dict] = {}
        for f in forecast_list:
            date = datetime.fromtimestamp(f["dt"], timezone.utc).date()
            date_str = str(date)
            if date_str not in daily:
                daily[date_str] = {"clouds": [], "conditions": []}
            daily[date_str]["clouds"].append(f["clouds"]["all"])
            daily[date_str]["conditions"].append(f["weather"][0]["main"])

        return [
            {
                "date": date,
                "avg_clouds": sum(data["clouds"]) / len(data["clouds"]),
                "conditions": max(set(data["conditions"]), key=data["conditions"].count)
            }
            for date, data in daily.items()
        ]

    def has_api_configured(self) -> bool:
        """Check if any weather API is configured."""
        return bool(
            self.apis["openweathermap"]["key"] or
            self.apis["weatherapi"]["key"]
        )
