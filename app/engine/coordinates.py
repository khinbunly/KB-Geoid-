"""Coordinate parsing and normalization module (DD, DMS, UTM)."""

import re
from dataclasses import dataclass
from typing import Optional, Tuple
import pyproj
from app.utils.logger import logger


@dataclass
class ParsedCoordinate:
    """Represents parsed coordinates with optional height and format information."""
    lat: float
    lon: float
    height: Optional[float] = None
    height_type: Optional[str] = None  # 'msl', 'ellipsoid', or None
    raw_input: str = ""
    coord_format: str = "Decimal Degrees"  # 'Decimal Degrees', 'DMS', 'UTM'
    utm_zone: Optional[str] = None
    utm_easting: Optional[float] = None
    utm_northing: Optional[float] = None


class CoordinateParser:
    """Parser for various geographic coordinate representations."""

    # Regex for DMS components: e.g. 6° 10' 31.41" S
    DMS_REGEX = re.compile(
        r"""
        (?P<deg>\d{1,3})\s*(?:[°ºd\s])\s*
        (?P<min>\d{1,2})\s*(?:['’m\s])\s*
        (?P<sec>\d{1,2}(?:\.\d+)?)\s*(?:["”s\s]*)?\s*
        (?P<hemi>[NSEWnsew])
        """,
        re.VERBOSE,
    )

    # Robust UTM Pattern 1: Zone [Band] Easting Northing [Height]
    # Examples:
    #   "48M 593596.681 1224909.7 5.129m"
    #   "48S 702315 9317050 50"
    #   "Zone 48S Easting 702315 Northing 9317050 Elevation 50m"
    #   "UTM 48N 500000 4649776 100m"
    UTM_PREFIX_REGEX = re.compile(
        r"""
        ^(?:utm\s*)?
        (?:zone\s*)?
        (?P<zone>\d{1,2})\s*
        (?P<band_or_hemi>[A-Za-z]+)?\s*
        [,\s:=]+
        (?:e(?:asting)?\s*[:=]?\s*)?
        (?P<easting>\d{5,7}(?:\.\d+)?)\s*(?:m|meter|meters)?\s*
        [,\s:=]+
        (?:n(?:orthing)?\s*[:=]?\s*)?
        (?P<northing>\d{6,8}(?:\.\d+)?)\s*(?:m|meter|meters)?\s*
        (?:[,\s:=]+(?:h(?:eight)?|elev|elevation|msl|ellips|tinggi)?\s*[:=]?\s*(?P<height>-?\d+(?:\.\d+)?)\s*(?:m|meter|meters)?)?
        \s*$
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    # UTM Pattern 2: Easting Northing Zone [Height]
    # Examples:
    #   "593596.681 1224909.7 48M 5.129m"
    #   "702315 9317050 48S 50"
    UTM_SUFFIX_REGEX = re.compile(
        r"""
        ^(?:e(?:asting)?\s*[:=]?\s*)?
        (?P<easting>\d{5,7}(?:\.\d+)?)\s*(?:m|meter|meters)?\s*
        [,\s:=]+
        (?:n(?:orthing)?\s*[:=]?\s*)?
        (?P<northing>\d{6,8}(?:\.\d+)?)\s*(?:m|meter|meters)?\s*
        [,\s:=]+
        (?:zone\s*)?
        (?P<zone>\d{1,2})\s*
        (?P<band_or_hemi>[A-Za-z]+)?\s*
        (?:[,\s:=]+(?:h(?:eight)?|elev|elevation|msl|ellips|tinggi)?\s*[:=]?\s*(?P<height>-?\d+(?:\.\d+)?)\s*(?:m|meter|meters)?)?
        \s*$
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    # UTM Pattern 3: Key-Value style: E=702315, N=9317050, Zone=48S, H=50m
    UTM_KV_ZONE_REGEX = re.compile(r"(?:utm\s*)?zone\s*[:=]?\s*(?P<zone>\d{1,2})\s*(?P<band>[A-Za-z]+)?", re.I)
    UTM_KV_EAST_REGEX = re.compile(r"(?:easting|east|e|x)\s*[:=]?\s*(?P<val>\d{5,7}(?:\.\d+)?)\s*(?:m|meter|meters)?", re.I)
    UTM_KV_NORTH_REGEX = re.compile(r"(?:northing|north|n|y)\s*[:=]?\s*(?P<val>\d{6,8}(?:\.\d+)?)\s*(?:m|meter|meters)?", re.I)
    UTM_KV_HEIGHT_REGEX = re.compile(r"(?:h(?:eight)?|elev|elevation|msl|ellips|z|tinggi)\s*[:=]?\s*(?P<val>-?\d+(?:\.\d+)?)\s*(?:m|meter|meters)?", re.I)

    @classmethod
    def parse_dms_component(cls, deg: float, minute: float, sec: float, hemi: str) -> float:
        """Convert Deg/Min/Sec + Hemisphere to Signed Decimal Degrees."""
        dd = float(deg) + float(minute) / 60.0 + float(sec) / 3600.0
        if hemi.upper() in ["S", "W"]:
            dd = -dd
        return dd

    @classmethod
    def utm_to_latlon(
        cls, zone_num: int, band_or_hemi: Optional[str], easting: float, northing: float
    ) -> Tuple[float, float, str]:
        """Convert UTM Easting/Northing to WGS84 Lat/Lon with intelligent hemisphere detection."""
        clean_band = (band_or_hemi or "").upper().strip()

        # Disambiguate Hemisphere:
        # In UTM surveying:
        # - If explicit "SOUTH" -> South
        # - If "S" and northing > 4,000,000 m -> South (e.g. Jakarta 9.3M m)
        # - If "S" but northing < 4,000,000 m (user meant MGRS band S, which is North 32°N-40°N, or typo for South)
        # - If northing > 5,000,000 m (Southern hemisphere false northing 10,000,000 m at equator)
        # - Otherwise (northing < 5,000,000 m) -> Northern hemisphere (0 to 5,000,000 m North of Equator)
        if clean_band in ["SOUTH"]:
            is_south = True
        elif clean_band in ["NORTH", "N"]:
            is_south = False
        elif clean_band == "S" and northing > 4000000:
            is_south = True
        elif northing > 5000000:
            is_south = True
        else:
            is_south = False

        if not (1 <= zone_num <= 60):
            raise ValueError(f"Invalid UTM Zone `{zone_num}`. Must be between 1 and 60.")

        epsg_code = 32700 + zone_num if is_south else 32600 + zone_num
        transformer = pyproj.Transformer.from_crs(f"EPSG:{epsg_code}", "EPSG:4326", always_xy=True)
        lon, lat = transformer.transform(easting, northing)

        hemi_str = "S" if is_south else "N"
        zone_label = f"{zone_num}{clean_band if clean_band else hemi_str}"
        return lat, lon, zone_label

    @classmethod
    def parse(cls, text: str) -> ParsedCoordinate:
        """
        Parse an input string containing coordinates in UTM, DMS, or DD format.
        """
        raw = text.strip()
        cleaned = raw.replace("\t", " ").strip()

        # Check for explicit height indicator keywords
        height = None
        height_type = None
        
        msl_match = re.search(r"(?:msl|ortho|orthometric|H)\s*[:=]?\s*(-?\d+(?:\.\d+)?)\s*(?:m|meter|meters)?", cleaned, re.I)
        if msl_match:
            height = float(msl_match.group(1))
            height_type = "msl"

        ellips_match = re.search(r"(?:ellips|ellipsoid|ellipsoidal|h)\s*[:=]?\s*(-?\d+(?:\.\d+)?)\s*(?:m|meter|meters)?", cleaned, re.I)
        if ellips_match:
            height = float(ellips_match.group(1))
            height_type = "ellipsoid"

        # 1. Try UTM Pattern 1: "48M 593596.681 1224909.7 5.129m", "48S 702315 9317050"
        m1 = cls.UTM_PREFIX_REGEX.match(cleaned)
        if m1:
            zone_num = int(m1.group("zone"))
            band = m1.group("band_or_hemi")
            easting = float(m1.group("easting"))
            northing = float(m1.group("northing"))
            if m1.group("height") and height is None:
                height = float(m1.group("height"))

            lat, lon, zone_str = cls.utm_to_latlon(zone_num, band, easting, northing)
            return ParsedCoordinate(
                lat=round(lat, 7),
                lon=round(lon, 7),
                height=height,
                height_type=height_type,
                raw_input=raw,
                coord_format="UTM",
                utm_zone=zone_str,
                utm_easting=easting,
                utm_northing=northing,
            )

        # 2. Try UTM Pattern 2: "593596.681 1224909.7 48M 5.129m"
        m2 = cls.UTM_SUFFIX_REGEX.match(cleaned)
        if m2:
            zone_num = int(m2.group("zone"))
            band = m2.group("band_or_hemi")
            easting = float(m2.group("easting"))
            northing = float(m2.group("northing"))
            if m2.group("height") and height is None:
                height = float(m2.group("height"))

            lat, lon, zone_str = cls.utm_to_latlon(zone_num, band, easting, northing)
            return ParsedCoordinate(
                lat=round(lat, 7),
                lon=round(lon, 7),
                height=height,
                height_type=height_type,
                raw_input=raw,
                coord_format="UTM",
                utm_zone=zone_str,
                utm_easting=easting,
                utm_northing=northing,
            )

        # 3. Try UTM Key-Value style: E=593596.681, N=1224909.7, Zone=48M, H=5.129m
        m_zone = cls.UTM_KV_ZONE_REGEX.search(cleaned)
        m_east = cls.UTM_KV_EAST_REGEX.search(cleaned)
        m_north = cls.UTM_KV_NORTH_REGEX.search(cleaned)
        if m_zone and m_east and m_north:
            zone_num = int(m_zone.group("zone"))
            band = m_zone.group("band")
            easting = float(m_east.group("val"))
            northing = float(m_north.group("val"))
            m_h = cls.UTM_KV_HEIGHT_REGEX.search(cleaned)
            if m_h and height is None:
                height = float(m_h.group("val"))

            lat, lon, zone_str = cls.utm_to_latlon(zone_num, band, easting, northing)
            return ParsedCoordinate(
                lat=round(lat, 7),
                lon=round(lon, 7),
                height=height,
                height_type=height_type,
                raw_input=raw,
                coord_format="UTM",
                utm_zone=zone_str,
                utm_easting=easting,
                utm_northing=northing,
            )

        # 4. Try DMS parsing
        dms_matches = list(cls.DMS_REGEX.finditer(cleaned))
        if len(dms_matches) >= 2:
            m_dms1, m_dms2 = dms_matches[0], dms_matches[1]
            val1 = cls.parse_dms_component(
                float(m_dms1.group("deg")), float(m_dms1.group("min")), float(m_dms1.group("sec")), m_dms1.group("hemi")
            )
            val2 = cls.parse_dms_component(
                float(m_dms2.group("deg")), float(m_dms2.group("min")), float(m_dms2.group("sec")), m_dms2.group("hemi")
            )

            h1 = m_dms1.group("hemi").upper()
            h2 = m_dms2.group("hemi").upper()

            if h1 in ["N", "S"] and h2 in ["E", "W"]:
                lat, lon = val1, val2
            elif h1 in ["E", "W"] and h2 in ["N", "S"]:
                lon, lat = val1, val2
            else:
                lat, lon = val1, val2

            if height is None:
                after_dms = cleaned[m_dms2.end():].strip()
                h_match = re.search(r"[-+]?\d+(?:\.\d+)?", after_dms)
                if h_match:
                    height = float(h_match.group(0))

            return ParsedCoordinate(
                lat=round(lat, 7),
                lon=round(lon, 7),
                height=height,
                height_type=height_type,
                raw_input=raw,
                coord_format="DMS",
            )

        # 5. Try Decimal Degrees (DD)
        # Remove trailing unit labels like 'm', 'meters'
        norm_text = re.sub(r"[a-zA-Z_]+[:=]", " ", cleaned)
        norm_text = re.sub(r"(?<=\d)\s*(?:m|meter|meters)\b", "", norm_text, flags=re.I)
        tokens = re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", norm_text)
        
        if len(tokens) >= 2:
            lat = float(tokens[0])
            lon = float(tokens[1])
            if len(tokens) >= 3 and height is None:
                height = float(tokens[2])

            return ParsedCoordinate(
                lat=round(lat, 7),
                lon=round(lon, 7),
                height=height,
                height_type=height_type,
                raw_input=raw,
                coord_format="Decimal Degrees",
            )

        raise ValueError(
            f"Could not parse coordinates from: '{text}'.\n\n"
            f"Supported formats:\n"
            f" • <b>UTM:</b> <code>48M 593596.681 1224909.7 5.129m</code>\n"
            f" • <b>UTM:</b> <code>48S 702315 9317050 50</code>\n"
            f" • <b>DD:</b> <code>-6.175392, 106.827153, 50</code>\n"
            f" • <b>DMS:</b> <code>6°10'31.4\"S 106°49'37.8\"E</code>"
        )

    @classmethod
    def format_dms(cls, lat: float, lon: float) -> str:
        """Convert Decimal Degrees to DMS string representation."""
        def dd_to_dms(val: float, is_lat: bool) -> str:
            hemi = ("N" if val >= 0 else "S") if is_lat else ("E" if val >= 0 else "W")
            abs_val = abs(val)
            d = int(abs_val)
            rem = (abs_val - d) * 60.0
            m = int(rem)
            s = (rem - m) * 60.0
            return f"{d:02d}°{m:02d}'{s:05.2f}\"{hemi}"

        return f"{dd_to_dms(lat, True)} {dd_to_dms(lon, False)}"

    @classmethod
    def to_utm(cls, lat: float, lon: float) -> str:
        """Convert Decimal Degrees to UTM string representation."""
        zone_num = int((lon + 180.0) // 6) + 1
        is_south = lat < 0
        epsg = 32700 + zone_num if is_south else 32600 + zone_num
        transformer = pyproj.Transformer.from_crs("EPSG:4326", f"EPSG:{epsg}", always_xy=True)
        easting, northing = transformer.transform(lon, lat)
        hemi = "S" if is_south else "N"
        return f"{zone_num}{hemi} {easting:06.2f}m E  {northing:07.2f}m N"
