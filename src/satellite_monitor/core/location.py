"""Geographic location handling for satellite monitoring."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field

import requests

logger = logging.getLogger(__name__)


@dataclass
class Location:
    """Geographic location for satellite monitoring.

    Attributes:
        name: Human-readable location name
        latitude: Latitude in decimal degrees (-90 to 90)
        longitude: Longitude in decimal degrees (-180 to 180)
        elevation_m: Elevation above sea level in meters
    """
    name: str
    latitude: float
    longitude: float
    elevation_m: float = 0

    def __post_init__(self):
        if not -90 <= self.latitude <= 90:
            raise ValueError(f"Latitude must be between -90 and 90, got {self.latitude}")
        if not -180 <= self.longitude <= 180:
            raise ValueError(f"Longitude must be between -180 and 180, got {self.longitude}")

    @classmethod
    def brussels(cls) -> Location:
        """Create a Location for Brussels, Belgium."""
        return cls(name="Brussels", latitude=50.8503, longitude=4.3517, elevation_m=100)

    @classmethod
    def from_coordinates(cls, latitude: float, longitude: float,
                         name: str | None = None) -> Location:
        """Create a Location from coordinates with optional name."""
        location_name = name or f"Location ({latitude:.4f}, {longitude:.4f})"
        return cls(name=location_name, latitude=latitude, longitude=longitude)


@dataclass
class Area:
    """Geographic bounding box area for satellite imagery.

    Attributes:
        name: Human-readable area name
        min_lon: Minimum longitude (western boundary)
        max_lon: Maximum longitude (eastern boundary)
        min_lat: Minimum latitude (southern boundary)
        max_lat: Maximum latitude (northern boundary)
    """
    name: str
    min_lon: float
    max_lon: float
    min_lat: float
    max_lat: float
    _area_sqkm: float | None = field(default=None, repr=False)

    def __post_init__(self):
        if self.min_lon >= self.max_lon:
            raise ValueError("min_lon must be less than max_lon")
        if self.min_lat >= self.max_lat:
            raise ValueError("min_lat must be less than max_lat")

    @classmethod
    def brussels(cls) -> Area:
        """Create an Area for Brussels metropolitan region."""
        return cls(
            name="Brussels",
            min_lon=4.2,
            max_lon=4.5,
            min_lat=50.75,
            max_lat=50.95
        )

    @classmethod
    def from_center(cls, name: str, latitude: float, longitude: float,
                    radius_km: float = 15) -> Area:
        """Create an Area from a center point and radius.

        Args:
            name: Human-readable area name
            latitude: Center latitude
            longitude: Center longitude
            radius_km: Radius from center in kilometers
        """
        # Approximate degrees per km
        lat_deg_per_km = 1 / 111.32
        lon_deg_per_km = 1 / (111.32 * math.cos(math.radians(latitude)))

        delta_lat = radius_km * lat_deg_per_km
        delta_lon = radius_km * lon_deg_per_km

        return cls(
            name=name,
            min_lon=longitude - delta_lon,
            max_lon=longitude + delta_lon,
            min_lat=latitude - delta_lat,
            max_lat=latitude + delta_lat
        )

    @classmethod
    def from_location(cls, location: Location, radius_km: float = 15) -> Area:
        """Create an Area centered on a Location."""
        return cls.from_center(
            name=location.name,
            latitude=location.latitude,
            longitude=location.longitude,
            radius_km=radius_km
        )

    @property
    def area_sqkm(self) -> float:
        """Calculate approximate area in square kilometers."""
        if self._area_sqkm is not None:
            return self._area_sqkm

        # Calculate using center latitude for longitude scaling
        center_lat = (self.min_lat + self.max_lat) / 2
        lat_km = 111.32  # km per degree latitude
        lon_km = 111.32 * math.cos(math.radians(center_lat))

        width_km = (self.max_lon - self.min_lon) * lon_km
        height_km = (self.max_lat - self.min_lat) * lat_km

        return width_km * height_km

    @property
    def center(self) -> tuple[float, float]:
        """Get the center coordinates (latitude, longitude)."""
        return (
            (self.min_lat + self.max_lat) / 2,
            (self.min_lon + self.max_lon) / 2
        )

    def to_wkt(self) -> str:
        """Convert to Well-Known Text (WKT) polygon format.

        Returns WKT POLYGON string suitable for geospatial APIs.
        """
        return (
            f"POLYGON(("
            f"{self.min_lon} {self.min_lat}, "
            f"{self.max_lon} {self.min_lat}, "
            f"{self.max_lon} {self.max_lat}, "
            f"{self.min_lon} {self.max_lat}, "
            f"{self.min_lon} {self.min_lat}))"
        )

    def to_bbox(self) -> dict[str, float]:
        """Convert to bounding box dictionary."""
        return {
            "min_lon": self.min_lon,
            "max_lon": self.max_lon,
            "min_lat": self.min_lat,
            "max_lat": self.max_lat,
        }

    def contains(self, latitude: float, longitude: float) -> bool:
        """Check if a point is within this area."""
        return (
            self.min_lat <= latitude <= self.max_lat and
            self.min_lon <= longitude <= self.max_lon
        )


# Preset locations for quick lookup (no geocoding needed)
PRESET_LOCATIONS: dict[str, tuple[float, float, float]] = {
    # Format: "name": (latitude, longitude, elevation_m)
    # Europe
    "brussels": (50.8503, 4.3517, 100),
    "london": (51.5074, -0.1278, 11),
    "paris": (48.8566, 2.3522, 35),
    "amsterdam": (52.3676, 4.9041, -2),
    "berlin": (52.5200, 13.4050, 34),
    "rome": (41.9028, 12.4964, 21),
    "madrid": (40.4168, -3.7038, 667),
    "vienna": (48.2082, 16.3738, 171),
    "prague": (50.0755, 14.4378, 235),
    "stockholm": (59.3293, 18.0686, 28),
    "oslo": (59.9139, 10.7522, 23),
    "copenhagen": (55.6761, 12.5683, 14),
    "helsinki": (60.1699, 24.9384, 26),
    "dublin": (53.3498, -6.2603, 20),
    "lisbon": (38.7223, -9.1393, 2),
    "zurich": (47.3769, 8.5417, 408),
    "geneva": (46.2044, 6.1432, 375),
    "munich": (48.1351, 11.5820, 519),
    "barcelona": (41.3851, 2.1734, 12),
    "milan": (45.4642, 9.1900, 120),
    # North America
    "new york": (40.7128, -74.0060, 10),
    "los angeles": (34.0522, -118.2437, 71),
    "san francisco": (37.7749, -122.4194, 16),
    "chicago": (41.8781, -87.6298, 181),
    "washington dc": (38.9072, -77.0369, 22),
    "boston": (42.3601, -71.0589, 14),
    "seattle": (47.6062, -122.3321, 56),
    "denver": (39.7392, -104.9903, 1609),
    "toronto": (43.6532, -79.3832, 76),
    "vancouver": (49.2827, -123.1207, 0),
    "montreal": (45.5017, -73.5673, 216),
    "mexico city": (19.4326, -99.1332, 2240),
    # Asia
    "tokyo": (35.6762, 139.6503, 40),
    "beijing": (39.9042, 116.4074, 43),
    "shanghai": (31.2304, 121.4737, 4),
    "hong kong": (22.3193, 114.1694, 32),
    "singapore": (1.3521, 103.8198, 15),
    "seoul": (37.5665, 126.9780, 38),
    "mumbai": (19.0760, 72.8777, 14),
    "delhi": (28.7041, 77.1025, 216),
    "bangalore": (12.9716, 77.5946, 920),
    "bangkok": (13.7563, 100.5018, 1),
    "dubai": (25.2048, 55.2708, 5),
    "tel aviv": (32.0853, 34.7818, 5),
    # Oceania
    "sydney": (-33.8688, 151.2093, 58),
    "melbourne": (-37.8136, 144.9631, 31),
    "auckland": (-36.8485, 174.7633, 63),
    "perth": (-31.9505, 115.8605, 31),
    # South America
    "sao paulo": (-23.5505, -46.6333, 760),
    "rio de janeiro": (-22.9068, -43.1729, 11),
    "buenos aires": (-34.6037, -58.3816, 25),
    "santiago": (-33.4489, -70.6693, 520),
    "bogota": (4.7110, -74.0721, 2640),
    "lima": (-12.0464, -77.0428, 154),
    # Africa
    "cairo": (30.0444, 31.2357, 75),
    "cape town": (-33.9249, 18.4241, 0),
    "johannesburg": (-26.2041, 28.0473, 1753),
    "nairobi": (-1.2921, 36.8219, 1795),
    "lagos": (6.5244, 3.3792, 41),
    "casablanca": (33.5731, -7.5898, 27),
}


def _geocode_nominatim(place_name: str) -> Location | None:
    """Geocode a place name using OpenStreetMap Nominatim.

    Args:
        place_name: Name of the place to geocode

    Returns:
        Location if found, None otherwise
    """
    try:
        response = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={
                "q": place_name,
                "format": "json",
                "limit": 1,
            },
            headers={
                "User-Agent": "satellite-monitor/1.0 (https://github.com/satellite-monitor)"
            },
            timeout=5,
        )

        if response.status_code != 200:
            logger.warning(f"Nominatim returned status {response.status_code}")
            return None

        results = response.json()
        if not results:
            logger.warning(f"No results found for '{place_name}'")
            return None

        result = results[0]
        return Location(
            name=result.get("display_name", place_name).split(",")[0],
            latitude=float(result["lat"]),
            longitude=float(result["lon"]),
        )

    except requests.RequestException as e:
        logger.warning(f"Nominatim request failed: {e}")
        return None
    except (KeyError, ValueError) as e:
        logger.warning(f"Failed to parse Nominatim response: {e}")
        return None


def resolve_location(name: str) -> Location | None:
    """Resolve a place name to a Location.

    First checks preset locations for fast lookup, then falls back to
    Nominatim geocoding for unknown locations.

    Args:
        name: Place name (e.g., "London", "Paris", "New York")

    Returns:
        Location if found, None otherwise

    Example:
        >>> loc = resolve_location("London")
        >>> print(f"{loc.name}: {loc.latitude}, {loc.longitude}")
        London: 51.5074, -0.1278
    """
    # Normalize the name for lookup
    normalized = name.lower().strip()

    # Check presets first
    if normalized in PRESET_LOCATIONS:
        lat, lon, elev = PRESET_LOCATIONS[normalized]
        # Use the original case-preserved name from user input
        display_name = name.title() if name.islower() else name
        return Location(
            name=display_name,
            latitude=lat,
            longitude=lon,
            elevation_m=elev,
        )

    # Fall back to Nominatim geocoding
    logger.info(f"'{name}' not in presets, trying Nominatim geocoding...")
    return _geocode_nominatim(name)


def get_preset_location_names() -> list[str]:
    """Get list of all preset location names.

    Returns:
        Sorted list of preset location names
    """
    return sorted(PRESET_LOCATIONS.keys())
