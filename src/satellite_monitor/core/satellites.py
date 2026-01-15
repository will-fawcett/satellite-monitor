"""Satellite specifications and catalog."""

from dataclasses import dataclass

from .providers import SatelliteProvider


@dataclass
class SatelliteSpecs:
    """Specifications for a satellite constellation.

    Attributes:
        provider: The satellite operator/data provider
        satellites: List of individual satellite names in the constellation
        resolution_m: Best spatial resolution in meters
        revisit_time_days: Average revisit time in days
        spectral_bands: Number of spectral bands
        has_sar: Whether the satellite has SAR (Synthetic Aperture Radar)
        has_optical: Whether the satellite has optical imaging
        swath_width_km: Image swath width in kilometers
        data_latency_hours: (min, max) hours from acquisition to data availability
        cost_per_sqkm: (min, max) cost per square kilometer in USD
        free_tier: Whether free access is available
        api_available: Whether programmatic API access is available
        streaming_available: Whether real-time data streaming is available
    """
    provider: SatelliteProvider
    satellites: list[str]
    resolution_m: float
    revisit_time_days: float
    spectral_bands: int
    has_sar: bool
    has_optical: bool
    swath_width_km: float
    data_latency_hours: tuple[float, float]
    cost_per_sqkm: tuple[float, float]
    free_tier: bool
    api_available: bool
    streaming_available: bool

    @property
    def is_weather_independent(self) -> bool:
        """SAR satellites can image through clouds."""
        return self.has_sar

    @property
    def is_free(self) -> bool:
        """Check if data is free."""
        return self.cost_per_sqkm[0] == 0 and self.cost_per_sqkm[1] == 0

    def estimate_cost(self, area_sqkm: float) -> tuple[float, float]:
        """Estimate cost for a given area size.

        Args:
            area_sqkm: Area size in square kilometers

        Returns:
            Tuple of (min_cost, max_cost) in USD
        """
        return (
            self.cost_per_sqkm[0] * area_sqkm,
            self.cost_per_sqkm[1] * area_sqkm
        )


# Complete satellite constellation catalog
SATELLITE_CATALOG: dict[str, SatelliteSpecs] = {
    "Sentinel-1": SatelliteSpecs(
        provider=SatelliteProvider.SENTINEL_ESA,
        satellites=["Sentinel-1A", "Sentinel-1B"],
        resolution_m=5.0,
        revisit_time_days=6.0,
        spectral_bands=1,
        has_sar=True,
        has_optical=False,
        swath_width_km=250,
        data_latency_hours=(1, 3),
        cost_per_sqkm=(0, 0),
        free_tier=True,
        api_available=True,
        streaming_available=True,
    ),
    "Sentinel-2": SatelliteSpecs(
        provider=SatelliteProvider.SENTINEL_ESA,
        satellites=["Sentinel-2A", "Sentinel-2B"],
        resolution_m=10.0,
        revisit_time_days=5.0,
        spectral_bands=13,
        has_sar=False,
        has_optical=True,
        swath_width_km=290,
        data_latency_hours=(1, 3),
        cost_per_sqkm=(0, 0),
        free_tier=True,
        api_available=True,
        streaming_available=True,
    ),
    "WorldView-3": SatelliteSpecs(
        provider=SatelliteProvider.MAXAR,
        satellites=["WorldView-3"],
        resolution_m=0.31,
        revisit_time_days=1.0,
        spectral_bands=29,
        has_sar=False,
        has_optical=True,
        swath_width_km=13.1,
        data_latency_hours=(1, 24),
        cost_per_sqkm=(17.5, 35.0),
        free_tier=False,
        api_available=True,
        streaming_available=False,
    ),
    "WorldView-2": SatelliteSpecs(
        provider=SatelliteProvider.MAXAR,
        satellites=["WorldView-2"],
        resolution_m=0.46,
        revisit_time_days=1.1,
        spectral_bands=9,
        has_sar=False,
        has_optical=True,
        swath_width_km=16.4,
        data_latency_hours=(1, 24),
        cost_per_sqkm=(15.0, 30.0),
        free_tier=False,
        api_available=True,
        streaming_available=False,
    ),
    "PlanetScope": SatelliteSpecs(
        provider=SatelliteProvider.PLANET,
        satellites=[f"Dove-{i}" for i in range(1, 201)],
        resolution_m=3.0,
        revisit_time_days=1.0,
        spectral_bands=8,
        has_sar=False,
        has_optical=True,
        swath_width_km=32.5,
        data_latency_hours=(1, 12),
        cost_per_sqkm=(1.8, 3.5),
        free_tier=False,
        api_available=True,
        streaming_available=True,
    ),
    "SkySat": SatelliteSpecs(
        provider=SatelliteProvider.PLANET,
        satellites=[f"SkySat-{i}" for i in range(1, 22)],
        resolution_m=0.5,
        revisit_time_days=1.0,
        spectral_bands=4,
        has_sar=False,
        has_optical=True,
        swath_width_km=8.0,
        data_latency_hours=(1, 6),
        cost_per_sqkm=(8.0, 15.0),
        free_tier=False,
        api_available=True,
        streaming_available=True,
    ),
    "Pleiades": SatelliteSpecs(
        provider=SatelliteProvider.AIRBUS,
        satellites=["Pleiades-1A", "Pleiades-1B", "Pleiades-Neo-3", "Pleiades-Neo-4"],
        resolution_m=0.3,
        revisit_time_days=1.0,
        spectral_bands=6,
        has_sar=False,
        has_optical=True,
        swath_width_km=20.0,
        data_latency_hours=(1, 24),
        cost_per_sqkm=(20.0, 40.0),
        free_tier=False,
        api_available=True,
        streaming_available=False,
    ),
    "SPOT": SatelliteSpecs(
        provider=SatelliteProvider.AIRBUS,
        satellites=["SPOT-6", "SPOT-7"],
        resolution_m=1.5,
        revisit_time_days=1.0,
        spectral_bands=5,
        has_sar=False,
        has_optical=True,
        swath_width_km=60.0,
        data_latency_hours=(2, 24),
        cost_per_sqkm=(5.0, 10.0),
        free_tier=False,
        api_available=True,
        streaming_available=False,
    ),
    "BlackSky": SatelliteSpecs(
        provider=SatelliteProvider.BLACKSKY,
        satellites=[f"Global-{i}" for i in range(1, 17)],
        resolution_m=1.0,
        revisit_time_days=1.0,
        spectral_bands=3,
        has_sar=False,
        has_optical=True,
        swath_width_km=5.0,
        data_latency_hours=(0.5, 2),
        cost_per_sqkm=(3.0, 6.0),
        free_tier=False,
        api_available=True,
        streaming_available=True,
    ),
    "ICEYE": SatelliteSpecs(
        provider=SatelliteProvider.ICEYE,
        satellites=[f"ICEYE-X{i}" for i in range(1, 32)],
        resolution_m=0.25,
        revisit_time_days=1.0,
        spectral_bands=1,
        has_sar=True,
        has_optical=False,
        swath_width_km=5.0,
        data_latency_hours=(0.5, 3),
        cost_per_sqkm=(50.0, 150.0),
        free_tier=False,
        api_available=True,
        streaming_available=True,
    ),
    "Capella": SatelliteSpecs(
        provider=SatelliteProvider.CAPELLA,
        satellites=[f"Capella-{i}" for i in range(1, 11)],
        resolution_m=0.5,
        revisit_time_days=1.0,
        spectral_bands=1,
        has_sar=True,
        has_optical=False,
        swath_width_km=5.0,
        data_latency_hours=(0.5, 2),
        cost_per_sqkm=(40.0, 120.0),
        free_tier=False,
        api_available=True,
        streaming_available=True,
    ),
    "Landsat-9": SatelliteSpecs(
        provider=SatelliteProvider.LANDSAT_USGS,
        satellites=["Landsat-9"],
        resolution_m=15.0,
        revisit_time_days=16.0,
        spectral_bands=11,
        has_sar=False,
        has_optical=True,
        swath_width_km=185,
        data_latency_hours=(12, 48),
        cost_per_sqkm=(0, 0),
        free_tier=True,
        api_available=True,
        streaming_available=False,
    ),
}


def get_free_satellites() -> dict[str, SatelliteSpecs]:
    """Get all satellites with free data access."""
    return {name: spec for name, spec in SATELLITE_CATALOG.items() if spec.free_tier}


def get_sar_satellites() -> dict[str, SatelliteSpecs]:
    """Get all SAR-capable satellites (weather independent)."""
    return {name: spec for name, spec in SATELLITE_CATALOG.items() if spec.has_sar}


def get_optical_satellites() -> dict[str, SatelliteSpecs]:
    """Get all optical satellites."""
    return {name: spec for name, spec in SATELLITE_CATALOG.items() if spec.has_optical}


def get_satellites_by_resolution(max_resolution_m: float) -> dict[str, SatelliteSpecs]:
    """Get satellites with resolution better than or equal to specified value."""
    return {
        name: spec for name, spec in SATELLITE_CATALOG.items()
        if spec.resolution_m <= max_resolution_m
    }
