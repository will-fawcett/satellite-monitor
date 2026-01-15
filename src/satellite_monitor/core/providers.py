"""Satellite data provider definitions."""

from enum import Enum


class SatelliteProvider(Enum):
    """Satellite data providers and their characteristics."""

    # Public/Free providers
    SENTINEL_ESA = "Sentinel (ESA Copernicus)"
    LANDSAT_USGS = "Landsat (USGS)"

    # Commercial providers
    MAXAR = "Maxar (WorldView, GeoEye)"
    PLANET = "Planet Labs (PlanetScope, SkySat)"
    AIRBUS = "Airbus (Pleiades, SPOT)"
    BLACKSKY = "BlackSky Global"
    ICEYE = "ICEYE (SAR)"
    CAPELLA = "Capella Space (SAR)"
    UMBRA = "Umbra (SAR)"

    # Data aggregators/platforms
    CLOUDFFERRO = "CloudFerro (CREODIAS)"
    AWS = "AWS (Open Data & Commercial)"
    GOOGLE = "Google Earth Engine"
    AZURE = "Microsoft Planetary Computer"
    UP42 = "UP42 Marketplace"


# Provider ordering URLs
PROVIDER_URLS = {
    SatelliteProvider.SENTINEL_ESA: "https://scihub.copernicus.eu/dhus/",
    SatelliteProvider.MAXAR: "https://discover.maxar.com/",
    SatelliteProvider.PLANET: "https://www.planet.com/explorer/",
    SatelliteProvider.AIRBUS: "https://www.intelligence-airbusds.com/geostore/",
    SatelliteProvider.BLACKSKY: "https://platform.blacksky.com/",
    SatelliteProvider.ICEYE: "https://www.iceye.com/sar-data",
    SatelliteProvider.CAPELLA: "https://console.capellaspace.com/",
    SatelliteProvider.CLOUDFFERRO: "https://creodias.eu/",
    SatelliteProvider.AWS: "https://registry.opendata.aws/",
    SatelliteProvider.UP42: "https://console.up42.com/",
    SatelliteProvider.LANDSAT_USGS: "https://earthexplorer.usgs.gov/",
}


def get_provider_url(provider: SatelliteProvider) -> str | None:
    """Get the ordering/access URL for a provider."""
    return PROVIDER_URLS.get(provider)
