"""High-performance batch CSV and Excel file processor for Geoid calculations."""

import io
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Dict, Optional, Tuple, Union
import numpy as np
import pandas as pd
import pyproj
from app.config import settings
from app.engine.converter import ConversionMode
from app.engine.coordinates import CoordinateParser
from app.engine.geoid import geoid_engine
from app.utils.logger import logger


@dataclass
class BatchResult:
    """Summary of batch processing operation."""
    total_points: int
    execution_time_sec: float
    output_filename: str
    output_bytes: bytes
    min_undulation: float
    max_undulation: float
    mean_undulation: float
    detected_lat_col: str
    detected_lon_col: str
    detected_height_col: Optional[str] = None
    mode: ConversionMode = ConversionMode.UNDULATION_ONLY


class BatchProcessor:
    """Processes tabular datasets (CSV, TSV, XLSX) for batch geoid calculations."""

    # Candidate column names (case-insensitive)
    LAT_CANDIDATES = ["latitude", "lat", "lintang", "y", "deg_lat", "y_coord", "lat_dd"]
    LON_CANDIDATES = ["longitude", "lon", "long", "bujur", "x", "deg_lon", "x_coord", "lon_dd"]
    
    # UTM Candidates
    EASTING_CANDIDATES = ["easting", "east", "utm_e", "x_utm", "e", "x_coord_utm"]
    NORTHING_CANDIDATES = ["northing", "north", "utm_n", "y_utm", "n", "y_coord_utm"]
    ZONE_CANDIDATES = ["zone", "utm_zone", "utmzone", "zona", "utm_zona"]

    HEIGHT_CANDIDATES = [
        "height", "elevation", "elev", "alt", "altitude", "z", "h", "tinggi",
        "h_msl", "h_ellips", "msl", "ellipsoid", "orthometric", "gps_height"
    ]

    @classmethod
    def detect_columns(cls, df: pd.DataFrame) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
        """
        Auto-detect coordinate and height columns from DataFrame.
        Returns (lat_or_easting_col, lon_or_northing_col, height_col, zone_col).
        """
        cols_lower = {col.strip().lower(): col for col in df.columns}
        
        detected_lat = None
        detected_lon = None
        detected_height = None
        detected_zone = None

        # 1. Check for standard Geographic Lat / Lon first
        for candidate in cls.LAT_CANDIDATES:
            if candidate in cols_lower:
                detected_lat = cols_lower[candidate]
                break

        for candidate in cls.LON_CANDIDATES:
            if candidate in cols_lower:
                detected_lon = cols_lower[candidate]
                break

        for candidate in cls.HEIGHT_CANDIDATES:
            if candidate in cols_lower:
                detected_height = cols_lower[candidate]
                break

        for candidate in cls.ZONE_CANDIDATES:
            if candidate in cols_lower:
                detected_zone = cols_lower[candidate]
                break

        # 2. If no lat/lon, check for UTM Easting/Northing
        if not detected_lat or not detected_lon:
            for candidate in cls.EASTING_CANDIDATES:
                if candidate in cols_lower:
                    detected_lon = cols_lower[candidate]  # Easting is X
                    break

            for candidate in cls.NORTHING_CANDIDATES:
                if candidate in cols_lower:
                    detected_lat = cols_lower[candidate]  # Northing is Y
                    break

        return detected_lat, detected_lon, detected_height, detected_zone

    @classmethod
    def process_file(
        cls,
        file_content: Union[bytes, BinaryIO],
        filename: str,
        mode: ConversionMode = ConversionMode.UNDULATION_ONLY,
        custom_lat_col: Optional[str] = None,
        custom_lon_col: Optional[str] = None,
        custom_height_col: Optional[str] = None,
    ) -> BatchResult:
        """
        Read file, compute EGM2008 undulations and height conversions, and return result bytes.
        """
        start_time = time.time()
        file_ext = Path(filename).suffix.lower()

        # Load file into DataFrame
        if isinstance(file_content, bytes):
            bio = io.BytesIO(file_content)
        else:
            bio = file_content

        if file_ext in [".xlsx", ".xls"]:
            df = pd.read_excel(bio)
            is_excel = True
        elif file_ext in [".tsv"]:
            df = pd.read_csv(bio, sep="\t")
            is_excel = False
        else:
            try:
                df = pd.read_csv(bio)
            except Exception:
                bio.seek(0)
                df = pd.read_csv(bio, sep=None, engine="python")
            is_excel = False

        if len(df) > settings.MAX_BATCH_ROWS:
            raise ValueError(
                f"File contains {len(df):,} rows, which exceeds the limit of {settings.MAX_BATCH_ROWS:,} rows."
            )

        # Detect columns
        det_lat, det_lon, det_h, det_zone = cls.detect_columns(df)
        lat_col = custom_lat_col or det_lat
        lon_col = custom_lon_col or det_lon
        height_col = custom_height_col or det_h

        if not lat_col or not lon_col:
            raise ValueError(
                f"Could not automatically detect Coordinate columns.\n"
                f"Columns found: {list(df.columns)}\n"
                f"Please ensure columns are named like 'lat'/'lon' or 'easting'/'northing' (with optional 'zone')."
            )

        # Check if coordinates are UTM (easting/northing or large values > 1000)
        sample_y = pd.to_numeric(df[lat_col], errors="coerce").dropna()
        sample_x = pd.to_numeric(df[lon_col], errors="coerce").dropna()
        
        is_utm = False
        if (len(sample_y) > 0 and sample_y.iloc[0] > 1000) or (det_zone is not None):
            is_utm = True

        if is_utm:
            # Handle UTM conversion
            df["_clean_e"] = pd.to_numeric(df[lon_col], errors="coerce")
            df["_clean_n"] = pd.to_numeric(df[lat_col], errors="coerce")
            valid_mask = df["_clean_e"].notna() & df["_clean_n"].notna()
            
            # Default zone if not present
            zone_val = str(df[det_zone].iloc[0]) if (det_zone and det_zone in df.columns) else "48S"
            m = re.match(r"(?P<zone>\d{1,2})\s*(?P<band>[A-Z]?)", zone_val, re.I)
            zone_num = int(m.group("zone")) if m else 48
            band = m.group("band") if (m and m.group("band")) else "S"
            is_south = band.upper() in ["S", "SOUTH"] or band.upper() in "CDEFGHJKLM"
            epsg = 32700 + zone_num if is_south else 32600 + zone_num

            transformer = pyproj.Transformer.from_crs(f"EPSG:{epsg}", "EPSG:4326", always_xy=True)
            valid_e = df.loc[valid_mask, "_clean_e"].values
            valid_n = df.loc[valid_mask, "_clean_n"].values
            valid_lons, valid_lats = transformer.transform(valid_e, valid_n)
            
            df["Calculated_Lat"] = np.nan
            df["Calculated_Lon"] = np.nan
            df.loc[valid_mask, "Calculated_Lat"] = np.round(valid_lats, 7)
            df.loc[valid_mask, "Calculated_Lon"] = np.round(valid_lons, 7)
            df.drop(columns=["_clean_e", "_clean_n"], inplace=True)
        else:
            # Geographic Lat/Lon
            df["_clean_lat"] = pd.to_numeric(df[lat_col], errors="coerce")
            df["_clean_lon"] = pd.to_numeric(df[lon_col], errors="coerce")
            valid_mask = df["_clean_lat"].notna() & df["_clean_lon"].notna()
            valid_lats = df.loc[valid_mask, "_clean_lat"].values
            valid_lons = df.loc[valid_mask, "_clean_lon"].values
            df.drop(columns=["_clean_lat", "_clean_lon"], inplace=True)

        if not valid_mask.any():
            raise ValueError(f"No valid numeric coordinate pairs found in columns '{lat_col}' and '{lon_col}'.")

        # Perform vectorized EGM2008 calculation
        undulations = geoid_engine.get_undulations_batch(valid_lats, valid_lons)

        # Insert results into DataFrame
        df["Geoid_Undulation_N_m"] = np.nan
        df.loc[valid_mask, "Geoid_Undulation_N_m"] = np.round(undulations, 4)

        if height_col and height_col in df.columns:
            df["_clean_h"] = pd.to_numeric(df[height_col], errors="coerce")
            h_vals = df.loc[valid_mask, "_clean_h"].values

            if mode == ConversionMode.MSL_TO_ELLIPSOID:
                df["Ellipsoidal_Height_h_m"] = np.nan
                df.loc[valid_mask, "Ellipsoidal_Height_h_m"] = np.round(h_vals + undulations, 4)
            elif mode == ConversionMode.ELLIPSOID_TO_MSL:
                df["MSL_Height_H_m"] = np.nan
                df.loc[valid_mask, "MSL_Height_H_m"] = np.round(h_vals - undulations, 4)
            else:
                df["MSL_Height_H_m"] = np.round(h_vals - undulations, 4)
                df["Ellipsoidal_Height_h_m"] = np.round(h_vals + undulations, 4)

            df.drop(columns=["_clean_h"], inplace=True)

        df["EGM_Model"] = "EGM2008"

        # Export result
        out_bio = io.BytesIO()
        stem = Path(filename).stem
        if is_excel:
            out_filename = f"{stem}_egm2008_converted.xlsx"
            with pd.ExcelWriter(out_bio, engine="openpyxl") as writer:
                df.to_excel(writer, index=False)
        else:
            out_filename = f"{stem}_egm2008_converted.csv"
            df.to_csv(out_bio, index=False)

        out_bio.seek(0)
        out_bytes = out_bio.getvalue()
        elapsed = time.time() - start_time

        valid_undulations = undulations[~np.isnan(undulations)]
        min_n = float(np.min(valid_undulations)) if len(valid_undulations) > 0 else 0.0
        max_n = float(np.max(valid_undulations)) if len(valid_undulations) > 0 else 0.0
        mean_n = float(np.mean(valid_undulations)) if len(valid_undulations) > 0 else 0.0

        return BatchResult(
            total_points=int(valid_mask.sum()),
            execution_time_sec=round(elapsed, 3),
            output_filename=out_filename,
            output_bytes=out_bytes,
            min_undulation=round(min_n, 4),
            max_undulation=round(max_n, 4),
            mean_undulation=round(mean_n, 4),
            detected_lat_col=lat_col,
            detected_lon_col=lon_col,
            detected_height_col=height_col,
            mode=mode,
        )
