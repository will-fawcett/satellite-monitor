"""Core data structures for satellite monitoring."""

from .location import (
    Area,
    Location,
    PRESET_LOCATIONS,
    get_preset_location_names,
    resolve_location,
)
from .passes import SatellitePass
from .providers import PROVIDER_URLS, SatelliteProvider, get_provider_url
from .satellites import (
    SATELLITE_CATALOG,
    SatelliteSpecs,
    get_free_satellites,
    get_optical_satellites,
    get_sar_satellites,
    get_satellites_by_resolution,
)

__all__ = [
    # Location
    "Location",
    "Area",
    "PRESET_LOCATIONS",
    "resolve_location",
    "get_preset_location_names",
    # Providers
    "SatelliteProvider",
    "PROVIDER_URLS",
    "get_provider_url",
    # Satellites
    "SatelliteSpecs",
    "SATELLITE_CATALOG",
    "get_free_satellites",
    "get_sar_satellites",
    "get_optical_satellites",
    "get_satellites_by_resolution",
    # Passes
    "SatellitePass",
]
