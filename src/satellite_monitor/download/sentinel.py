"""Sentinel satellite data downloader using Copernicus Hub."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from ..core.location import Area

if TYPE_CHECKING:
    import pandas as pd
    from sentinelsat import SentinelAPI

logger = logging.getLogger(__name__)


@dataclass
class SentinelConfig:
    """Configuration for Sentinel data download.

    Attributes:
        username: Copernicus Hub username
        password: Copernicus Hub password
        download_dir: Directory for downloaded data
        days_back: How many days back to search
        max_cloud_coverage: Maximum cloud coverage percentage for Sentinel-2
        max_products: Maximum number of products to download per satellite
    """
    username: str = ""
    password: str = ""
    download_dir: Path = field(default_factory=lambda: Path("./sentinel_data"))
    days_back: int = 30
    max_cloud_coverage: int = 20
    max_products: int = 5

    @classmethod
    def from_env(cls, **kwargs) -> SentinelConfig:
        """Create config with credentials from environment variables.

        Environment variables:
            COPERNICUS_USERNAME: Hub username
            COPERNICUS_PASSWORD: Hub password
        """
        return cls(
            username=os.getenv("COPERNICUS_USERNAME", ""),
            password=os.getenv("COPERNICUS_PASSWORD", ""),
            **kwargs
        )


class SentinelDownloader:
    """Download Sentinel-1 and Sentinel-2 data from ESA Copernicus Hub.

    Requires the 'sentinel' optional dependencies:
        pip install satellite-monitor[sentinel]

    Example:
        config = SentinelConfig.from_env(days_back=14)
        downloader = SentinelDownloader(config)
        s1, s2 = downloader.run(download=False)  # Search only
    """

    def __init__(
        self,
        config: SentinelConfig,
        area: Area | None = None
    ):
        """Initialize the downloader.

        Args:
            config: Download configuration
            area: Target area. Defaults to Brussels.
        """
        self.config = config
        self.area = area or Area.brussels()
        self._api: SentinelAPI | None = None

        # Create download directory
        self.config.download_dir.mkdir(parents=True, exist_ok=True)

    @property
    def api(self) -> SentinelAPI:
        """Get the connected API instance."""
        if self._api is None:
            raise ValueError("Not connected to API. Call connect() first.")
        return self._api

    def connect(self) -> None:
        """Connect to Copernicus Open Access Hub."""
        try:
            from sentinelsat import SentinelAPI
        except ImportError as e:
            raise ImportError(
                "sentinelsat is required for downloading. "
                "Install with: pip install satellite-monitor[sentinel]"
            ) from e

        try:
            self._api = SentinelAPI(
                self.config.username,
                self.config.password,
                'https://apihub.copernicus.eu/apihub'
            )
            logger.info("Successfully connected to Copernicus Hub")
        except Exception as e:
            logger.error(f"Failed to connect to Copernicus Hub: {e}")
            raise

    def _get_wkt(self) -> str:
        """Get WKT representation of the area using shapely."""
        try:
            from shapely.geometry import box
        except ImportError as e:
            raise ImportError(
                "shapely is required for area definition. "
                "Install with: pip install satellite-monitor[sentinel]"
            ) from e

        bbox = box(
            self.area.min_lon,
            self.area.min_lat,
            self.area.max_lon,
            self.area.max_lat
        )
        return bbox.wkt

    def search_sentinel1(self) -> pd.DataFrame:
        """Search for Sentinel-1 SAR products.

        Returns:
            DataFrame with product information
        """
        import pandas as pd

        end_date = datetime.now()
        start_date = end_date - timedelta(days=self.config.days_back)

        logger.info(f"Searching Sentinel-1 products from {start_date} to {end_date}")

        products = self.api.query(
            self._get_wkt(),
            date=(start_date, end_date),
            platformname='Sentinel-1',
            producttype='GRD',
            sensoroperationalmode='IW',
        )

        df = self.api.to_dataframe(products)

        if not df.empty:
            df = df.sort_values('ingestiondate', ascending=False)
            df = df.head(self.config.max_products)
            logger.info(f"Found {len(df)} Sentinel-1 products")
        else:
            logger.warning("No Sentinel-1 products found")

        return df

    def search_sentinel2(self) -> pd.DataFrame:
        """Search for Sentinel-2 optical products.

        Returns:
            DataFrame with product information
        """
        import pandas as pd

        end_date = datetime.now()
        start_date = end_date - timedelta(days=self.config.days_back)

        logger.info(f"Searching Sentinel-2 products from {start_date} to {end_date}")

        products = self.api.query(
            self._get_wkt(),
            date=(start_date, end_date),
            platformname='Sentinel-2',
            producttype='S2MSI2A',
            cloudcoverpercentage=(0, self.config.max_cloud_coverage)
        )

        df = self.api.to_dataframe(products)

        if not df.empty:
            df = df.sort_values(
                ['ingestiondate', 'cloudcoverpercentage'],
                ascending=[False, True]
            )
            df = df.head(self.config.max_products)
            logger.info(f"Found {len(df)} Sentinel-2 products")
        else:
            logger.warning("No Sentinel-2 products found")

        return df

    def download_products(
        self,
        products_df: pd.DataFrame,
        satellite: Literal["Sentinel-1", "Sentinel-2"]
    ) -> None:
        """Download the selected products.

        Args:
            products_df: DataFrame of products to download
            satellite: Satellite type for directory naming
        """
        if products_df.empty:
            logger.warning(f"No {satellite} products to download")
            return

        sat_dir = self.config.download_dir / satellite.lower().replace('-', '')
        sat_dir.mkdir(exist_ok=True)

        logger.info(f"Downloading {len(products_df)} {satellite} products")

        for idx, (product_id, product_info) in enumerate(products_df.iterrows(), 1):
            try:
                logger.info(
                    f"[{idx}/{len(products_df)}] Downloading {product_info['title']}"
                )
                logger.info(f"  Size: {product_info['size']}")
                logger.info(f"  Date: {product_info['beginposition']}")

                if satellite == "Sentinel-2":
                    cloud = product_info.get('cloudcoverpercentage', 'N/A')
                    logger.info(f"  Cloud coverage: {cloud}%")

                self.api.download(product_id, directory_path=sat_dir)
                logger.info(f"  Successfully downloaded to {sat_dir}")

            except Exception as e:
                logger.error(f"  Failed to download {product_info['title']}: {e}")
                continue

    def save_metadata(
        self,
        s1_df: pd.DataFrame,
        s2_df: pd.DataFrame
    ) -> None:
        """Save metadata about downloaded products.

        Args:
            s1_df: Sentinel-1 products DataFrame
            s2_df: Sentinel-2 products DataFrame
        """
        metadata_file = self.config.download_dir / "download_metadata.json"

        metadata = {
            "download_date": datetime.now().isoformat(),
            "area": {
                "name": self.area.name,
                "bbox": self.area.to_bbox()
            },
            "sentinel1": {
                "products_found": len(s1_df),
                "products": s1_df.to_dict('records') if not s1_df.empty else []
            },
            "sentinel2": {
                "products_found": len(s2_df),
                "max_cloud_coverage": self.config.max_cloud_coverage,
                "products": s2_df.to_dict('records') if not s2_df.empty else []
            }
        }

        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2, default=str)

        logger.info(f"Metadata saved to {metadata_file}")

    def run(self, download: bool = True) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Execute search and optionally download.

        Args:
            download: If True, download products. If False, only search.

        Returns:
            Tuple of (Sentinel-1 DataFrame, Sentinel-2 DataFrame)
        """
        import pandas as pd

        self.connect()

        logger.info("=" * 50)
        logger.info("Searching for Sentinel-1 products...")
        s1_products = self.search_sentinel1()

        logger.info("=" * 50)
        logger.info("Searching for Sentinel-2 products...")
        s2_products = self.search_sentinel2()

        self.save_metadata(s1_products, s2_products)

        if download:
            logger.info("=" * 50)
            logger.info("Starting downloads...")
            self.download_products(s1_products, "Sentinel-1")
            self.download_products(s2_products, "Sentinel-2")
            logger.info("=" * 50)
            logger.info("Download complete!")
        else:
            logger.info("=" * 50)
            logger.info("Search complete (download skipped)")

        return s1_products, s2_products
