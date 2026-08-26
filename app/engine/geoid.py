"""EGM2008 Geoid Undulation Computation Engine."""

import os
from pathlib import Path
from typing import Tuple, Union, Optional
import numpy as np
import pyproj
from app.config import settings
from app.utils.logger import logger


class EGM2008Engine:
    """High-precision EGM2008 Geoid Undulation Engine using PROJ and GeographicLib."""

    def __init__(self):
        self._transformer_to_msl: Optional[pyproj.Transformer] = None
        self._transformer_to_ellipsoid: Optional[pyproj.Transformer] = None
        self._geographiclib_geoid = None
        self.backend_used = "unknown"
        self._initialize()

    def _initialize(self) -> None:
        """Initialize PROJ network and transformers."""
        # Enable PROJ network CDN if requested
        if settings.PROJ_NETWORK:
            try:
                pyproj.network.set_network_enabled(True)
                logger.info("PROJ network CDN enabled for EGM2008 grids")
            except Exception as e:
                logger.warning(f"Could not enable PROJ network: {e}")

        # Set custom PROJ cache dir if configured
        if settings.PROJ_CACHE_DIR:
            try:
                cache_dir = settings.BASE_DIR / settings.PROJ_CACHE_DIR
                cache_dir.mkdir(parents=True, exist_ok=True)
                # pyproj uses user cache automatically, but we ensure folder exists
            except Exception as e:
                logger.warning(f"Failed to create cache directory: {e}")

        # Try initializing PROJ 3D transformer (WGS84 3D <-> WGS84 + EGM2008 MSL)
        # EPSG:4979: Geographic 3D (lat, lon, ellipsoidal height)
        # EPSG:4326+3855: Geographic 2D (lat, lon) + EGM2008 height (MSL / orthometric)
        try:
            self._transformer_to_msl = pyproj.Transformer.from_crs(
                "EPSG:4979", "EPSG:4326+3855", always_xy=True
            )
            self._transformer_to_ellipsoid = pyproj.Transformer.from_crs(
                "EPSG:4326+3855", "EPSG:4979", always_xy=True
            )
            self.backend_used = "PROJ (EGM2008 EPSG:3855)"
            logger.info("Initialized PROJ EGM2008 transformer successfully")
        except Exception as e:
            logger.warning(f"PROJ EGM2008 initialization failed: {e}. Attempting fallback.")
            self._init_fallback()

    def _init_fallback(self) -> None:
        """Initialize GeographicLib geoid fallback if PROJ is unavailable."""
        try:
            import geographiclib.geoid
            # Attempt to load egm2008-5 or egm2008-1
            for model_name in ["egm2008-5", "egm2008-1", "egm2008-2_5", "egm96-5"]:
                try:
                    self._geographiclib_geoid = geographiclib.geoid.Geoid(model_name)
                    self.backend_used = f"GeographicLib ({model_name})"
                    logger.info(f"Initialized fallback geoid engine: {self.backend_used}")
                    return
                except Exception:
                    continue
            logger.warning("No local GeographicLib geoid dataset found; PROJ fallback active.")
        except Exception as e:
            logger.error(f"Failed to initialize GeographicLib fallback: {e}")

    def get_undulation(self, lat: float, lon: float) -> float:
        """
        Calculate EGM2008 Geoid Undulation N (meters) at given latitude and longitude.
        
        N = h (ellipsoidal) - H (orthometric/MSL)
        
        Args:
            lat: Latitude in decimal degrees [-90.0, 90.0]
            lon: Longitude in decimal degrees [-180.0, 180.0]
            
        Returns:
            Geoid separation N in meters (float)
        """
        # Ensure longitude is normalized to [-180, 180]
        lon = ((lon + 180.0) % 360.0) - 180.0
        
        # Primary: PROJ transformer with h = 0
        if self._transformer_to_msl is not None:
            try:
                _, _, h_msl = self._transformer_to_msl.transform(lon, lat, 0.0)
                # When ellipsoidal h = 0, H = -N, therefore N = -H = -h_msl
                return float(-h_msl)
            except Exception as e:
                logger.debug(f"PROJ calculation failed for ({lat}, {lon}): {e}, trying fallback")

        # Fallback: GeographicLib
        if self._geographiclib_geoid is not None:
            return float(self._geographiclib_geoid(lat, lon))

        raise RuntimeError("No geoid calculation engine is currently operational.")

    def get_undulations_batch(
        self, lats: Union[np.ndarray, list], lons: Union[np.ndarray, list]
    ) -> np.ndarray:
        """
        Vectorized calculation of Geoid Undulations N (meters) for arrays of coordinates.
        
        Args:
            lats: Array or list of latitudes in decimal degrees
            lons: Array or list of longitudes in decimal degrees
            
        Returns:
            NumPy 1D array of geoid undulations in meters
        """
        lats_arr = np.asarray(lats, dtype=np.float64)
        lons_arr = np.asarray(lons, dtype=np.float64)
        
        # Normalize longitudes to [-180, 180]
        lons_arr = ((lons_arr + 180.0) % 360.0) - 180.0
        zeros_h = np.zeros_like(lons_arr)

        if self._transformer_to_msl is not None:
            try:
                _, _, h_msl = self._transformer_to_msl.transform(lons_arr, lats_arr, zeros_h)
                return -np.asarray(h_msl, dtype=np.float64)
            except Exception as e:
                logger.warning(f"Vectorized PROJ transform failed: {e}. Falling back to scalar loop.")

        # Fallback element-wise
        undulations = np.empty(len(lats_arr), dtype=np.float64)
        for i in range(len(lats_arr)):
            undulations[i] = self.get_undulation(lats_arr[i], lons_arr[i])
        return undulations

    def info(self) -> dict:
        """Return engine metadata and operational status."""
        return {
            "model": "EGM2008 (Earth Gravitational Model 2008)",
            "backend": self.backend_used,
            "crs_ellipsoidal": "EPSG:4979 (WGS84 3D)",
            "crs_orthometric": "EPSG:4326+3855 (WGS84 2D + EGM2008 MSL)",
            "grid_resolution": "2.5 arc-minutes (~4.5 km)",
            "vertical_datum": "Mean Sea Level (Geoid)",
        }


# Global singleton instance
geoid_engine = EGM2008Engine()
