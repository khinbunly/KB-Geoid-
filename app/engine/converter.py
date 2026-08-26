"""MSL <-> Ellipsoidal Height Conversion Service."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple
import pandas as pd
from app.engine.geoid import EGM2008Engine, geoid_engine


class ConversionMode(str, Enum):
    """Supported conversion modes."""
    UNDULATION_ONLY = "undulation_only"
    MSL_TO_ELLIPSOID = "msl_to_ellipsoid"
    ELLIPSOID_TO_MSL = "ellipsoid_to_msl"


@dataclass
class PointResult:
    """Result of a geoid / height conversion calculation."""
    lat: float
    lon: float
    mode: ConversionMode
    geoid_undulation_n: float
    input_height: Optional[float] = None
    output_height: Optional[float] = None
    ellipsoidal_height_h: Optional[float] = None
    orthometric_height_H: Optional[float] = None
    formula_used: str = ""
    backend: str = "PROJ EGM2008"


class GeoidConverter:
    """Converts heights between MSL (Orthometric) and WGS84 Ellipsoid using EGM2008."""

    def __init__(self, engine: Optional[EGM2008Engine] = None):
        self.engine = engine or geoid_engine

    def convert_point(
        self,
        lat: float,
        lon: float,
        mode: ConversionMode = ConversionMode.UNDULATION_ONLY,
        input_height: Optional[float] = None,
    ) -> PointResult:
        """
        Perform conversion for a single point.
        
        Formula:
            h = H + N   (Ellipsoidal Height = MSL Height + Geoid Undulation)
            H = h - N   (MSL Height = Ellipsoidal Height - Geoid Undulation)
        """
        n = self.engine.get_undulation(lat, lon)
        backend = self.engine.backend_used

        if mode == ConversionMode.UNDULATION_ONLY:
            return PointResult(
                lat=lat,
                lon=lon,
                mode=mode,
                geoid_undulation_n=n,
                input_height=None,
                output_height=None,
                ellipsoidal_height_h=None,
                orthometric_height_H=None,
                formula_used="N = EGM2008(lat, lon)",
                backend=backend,
            )

        if input_height is None:
            raise ValueError("Input height must be provided for conversion modes.")

        if mode == ConversionMode.MSL_TO_ELLIPSOID:
            # Input is Orthometric/MSL Height H, output is Ellipsoidal Height h
            H = float(input_height)
            h = H + n
            return PointResult(
                lat=lat,
                lon=lon,
                mode=mode,
                input_height=H,
                output_height=h,
                geoid_undulation_n=n,
                ellipsoidal_height_h=h,
                orthometric_height_H=H,
                formula_used="h = H + N  (Ellipsoid = MSL + Geoid)",
                backend=backend,
            )

        elif mode == ConversionMode.ELLIPSOID_TO_MSL:
            # Input is Ellipsoidal Height h, output is Orthometric/MSL Height H
            h = float(input_height)
            H = h - n
            return PointResult(
                lat=lat,
                lon=lon,
                mode=mode,
                input_height=h,
                output_height=H,
                geoid_undulation_n=n,
                ellipsoidal_height_h=h,
                orthometric_height_H=H,
                formula_used="H = h - N  (MSL = Ellipsoid - Geoid)",
                backend=backend,
            )

        else:
            raise ValueError(f"Unsupported conversion mode: {mode}")

    def get_undulation(self, lat: float, lon: float) -> float:
        """Shorthand to calculate N."""
        return self.engine.get_undulation(lat, lon)

    def msl_to_ellipsoid(self, lat: float, lon: float, msl_height: float) -> Tuple[float, float]:
        """Convert MSL Height H to Ellipsoidal Height h. Returns (h, N)."""
        res = self.convert_point(lat, lon, ConversionMode.MSL_TO_ELLIPSOID, msl_height)
        return res.output_height, res.geoid_undulation_n

    def ellipsoid_to_msl(self, lat: float, lon: float, ellipsoid_height: float) -> Tuple[float, float]:
        """Convert Ellipsoidal Height h to MSL Height H. Returns (H, N)."""
        res = self.convert_point(lat, lon, ConversionMode.ELLIPSOID_TO_MSL, ellipsoid_height)
        return res.output_height, res.geoid_undulation_n


# Global singleton instance
geoid_converter = GeoidConverter()
