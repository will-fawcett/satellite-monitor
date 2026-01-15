"""Weather data models."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class WeatherData:
    """Current and forecast weather data.

    Attributes:
        current_cloud_cover: Cloud coverage percentage (0-100)
        current_visibility_km: Visibility in kilometers
        current_conditions: Human-readable conditions description
        forecast_24h: Hourly forecast data for next 24 hours
        forecast_daily: Daily forecast data
        last_updated: When this data was fetched
        sunrise: Today's sunrise time (UTC)
        sunset: Today's sunset time (UTC)
        is_daylight: Whether it's currently daylight
    """
    current_cloud_cover: float
    current_visibility_km: float
    current_conditions: str
    forecast_24h: list[dict]
    forecast_daily: list[dict]
    last_updated: datetime
    sunrise: datetime
    sunset: datetime
    is_daylight: bool

    @property
    def is_good_for_optical(self) -> bool:
        """Check if conditions are good for optical imaging."""
        return self.current_cloud_cover < 30 and self.is_daylight

    @property
    def is_marginal_for_optical(self) -> bool:
        """Check if conditions are marginal for optical imaging."""
        return 30 <= self.current_cloud_cover < 70 and self.is_daylight

    @property
    def is_poor_for_optical(self) -> bool:
        """Check if conditions are poor for optical imaging."""
        return self.current_cloud_cover >= 70 or not self.is_daylight

    def get_cloud_emoji(self) -> str:
        """Get an emoji representing current cloud conditions."""
        if self.current_cloud_cover < 20:
            return "sunny"
        elif self.current_cloud_cover < 40:
            return "partly_sunny"
        elif self.current_cloud_cover < 60:
            return "partly_cloudy"
        elif self.current_cloud_cover < 80:
            return "cloudy"
        else:
            return "rainy"


@dataclass
class SatelliteRecommendation:
    """Satellite recommendation based on weather conditions.

    Attributes:
        satellite_name: Name of the satellite
        provider: Data provider name
        score: Recommendation score (0-100, higher is better)
        reasons: List of factors affecting the score
        estimated_quality: Quality estimate ("Excellent", "Good", "Fair", "Poor")
        cost: Cost as formatted string (e.g., "FREE", "$1,000")
        eta_hours: Estimated hours until data available
        weather_suitable: Whether current weather is suitable
    """
    satellite_name: str
    provider: str
    score: float
    reasons: list[str]
    estimated_quality: str
    cost: str
    eta_hours: float
    weather_suitable: bool

    @property
    def is_free(self) -> bool:
        """Check if this option is free."""
        return self.cost == "FREE"

    def get_cost_value(self) -> float:
        """Extract numeric cost value."""
        if self.cost == "FREE":
            return 0.0
        return float(self.cost.replace("$", "").replace(",", ""))
