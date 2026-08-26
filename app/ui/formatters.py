"""HTML and Markdown presentation formatters for Telegram messages."""

import html
from typing import Optional
from app.engine.converter import ConversionMode, PointResult
from app.engine.coordinates import CoordinateParser, ParsedCoordinate
from app.engine.batch import BatchResult


def escape_html(text: str) -> str:
    """Escape text for Telegram HTML mode (preserving quotes for DMS symbols)."""
    return html.escape(str(text), quote=False)


def escape_markdown(text: str) -> str:
    """Escape text for Telegram MarkdownV2 mode."""
    escape_chars = r"_*[]()~`>#+-=|{}.!"
    return "".join(f"\\{c}" if c in escape_chars else c for c in str(text))


def format_point_result(res: PointResult, parsed: Optional[ParsedCoordinate] = None) -> str:
    """Format calculation result into a clean, modern HTML card."""
    dms_str = CoordinateParser.format_dms(res.lat, res.lon)
    utm_str = CoordinateParser.to_utm(res.lat, res.lon)

    sign_n = "+" if res.geoid_undulation_n >= 0 else ""
    n_formatted = f"{sign_n}{res.geoid_undulation_n:,.4f} m"

    is_utm_input = parsed and parsed.coord_format == "UTM"

    if is_utm_input:
        # Specialized UTM -> Lat/Lon & Ellipsoid Card
        lines = [
            "🗺️ <b>UTM ➔ Lat/Long & Ellipsoidal Height Result</b>",
            "━━━━━━━━━━━━━━━━━━━━━━",
            "📌 <b>Input UTM:</b>",
            f" • <b>Zone:</b> <code>{parsed.utm_zone or 'Auto'}</code>",
            f" • <b>Easting (X):</b> <code>{parsed.utm_easting:,.2f} m</code>" if parsed.utm_easting else "",
            f" • <b>Northing (Y):</b> <code>{parsed.utm_northing:,.2f} m</code>" if parsed.utm_northing else "",
            "",
            "🌐 <b>Converted Lat / Long (WGS84):</b>",
            f" • <b>DD:</b> <code>{res.lat:.7f}°, {res.lon:.7f}°</code>",
            f" • <b>DMS:</b> <code>{escape_html(dms_str)}</code>",
            "",
            f"📐 <b>EGM2008 Geoid Undulation (N):</b> <code>{n_formatted}</code>",
        ]
        lines = [line for line in lines if line != ""]

        if res.ellipsoidal_height_h is not None and res.orthometric_height_H is not None:
            lines.extend([
                "",
                "📊 <b>Height Conversion:</b>",
                f" • <b>Input MSL (H):</b> <code>{res.orthometric_height_H:,.4f} m</code>",
                f" • <b>Ellipsoidal Height (h):</b> <code>{res.ellipsoidal_height_h:,.4f} m</code>",
                f" • <i>Formula: h = H + N ({res.orthometric_height_H:,.4f} + {res.geoid_undulation_n:,.4f})</i>",
                "",
                "📋 <b>Copyable (Lat, Lon, Ellips_h):</b>",
                f"<code>{res.lat:.7f}, {res.lon:.7f}, {res.ellipsoidal_height_h:.4f}</code>",
            ])
        else:
            lines.extend([
                "",
                "💡 <i>Tip: Add elevation at the end of your UTM input to calculate exact Ellipsoidal Height (h).</i>",
                f"<i>Example: <code>{parsed.utm_zone} {int(parsed.utm_easting or 593596)} {int(parsed.utm_northing or 1224909)} 5.129m</code></i>",
                "",
                "📋 <b>Copyable (Lat, Lon):</b>",
                f"<code>{res.lat:.7f}, {res.lon:.7f}</code>",
            ])

        lines.extend([
            "",
            "⚙️ <b>Datum:</b> <code>WGS84 / EGM2008 2.5' Grid</code>",
            "━━━━━━━━━━━━━━━━━━━━━━",
        ])
        return "\n".join(lines)

    # Standard Lat/Lon Card
    lines = [
        "🌐 <b>EGM2008 Geoid Calculation Result</b>",
        "━━━━━━━━━━━━━━━━━━━━━━",
        "📍 <b>Coordinates:</b>",
        f" • <b>DD:</b> <code>{res.lat:.7f}, {res.lon:.7f}</code>",
        f" • <b>DMS:</b> <code>{escape_html(dms_str)}</code>",
        f" • <b>UTM:</b> <code>{escape_html(utm_str)}</code>",
        "",
        f"📐 <b>Geoid Undulation (N):</b> <code>{n_formatted}</code>",
    ]

    # Height conversion details
    if res.mode == ConversionMode.MSL_TO_ELLIPSOID and res.ellipsoidal_height_h is not None:
        lines.extend([
            "",
            "📊 <b>Height Conversion (MSL ➔ Ellipsoid):</b>",
            f" • <b>Input MSL (H):</b> <code>{res.orthometric_height_H:,.4f} m</code>",
            f" • <b>Ellipsoidal Height (h):</b> <code>{res.ellipsoidal_height_h:,.4f} m</code>",
            f" • <i>Formula: h = H + N</i>",
        ])
    elif res.mode == ConversionMode.ELLIPSOID_TO_MSL and res.orthometric_height_H is not None:
        lines.extend([
            "",
            "📊 <b>Height Conversion (Ellipsoid ➔ MSL):</b>",
            f" • <b>Input Ellipsoid (h):</b> <code>{res.ellipsoidal_height_h:,.4f} m</code>",
            f" • <b>MSL Height (H):</b> <code>{res.orthometric_height_H:,.4f} m</code>",
            f" • <i>Formula: H = h - N</i>",
        ])

    lines.extend([
        "",
        "⚙️ <b>Model:</b> <code>EGM2008 (WGS84 2.5' Grid)</code>",
        "━━━━━━━━━━━━━━━━━━━━━━",
    ])

    return "\n".join(lines)


def format_batch_result(res: BatchResult) -> str:
    """Format batch file conversion result summary."""
    lines = [
        "✅ <b>Batch Conversion Complete!</b>",
        "━━━━━━━━━━━━━━━━━━━━━━",
        f"📁 <b>Output File:</b> <code>{escape_html(res.output_filename)}</code>",
        f"📊 <b>Total Points Processed:</b> <code>{res.total_points:,}</code>",
        f"⚡ <b>Execution Time:</b> <code>{res.execution_time_sec:.3f} s</code>",
        "",
        "📈 <b>Geoid Undulation (N) Statistics:</b>",
        f" • <b>Minimum:</b> <code>{res.min_undulation:+.4f} m</code>",
        f" • <b>Average:</b> <code>{res.mean_undulation:+.4f} m</code>",
        f" • <b>Maximum:</b> <code>{res.max_undulation:+.4f} m</code>",
        "",
        "🔍 <b>Detected Columns:</b>",
        f" • Coord 1: <code>{escape_html(res.detected_lat_col)}</code>",
        f" • Coord 2: <code>{escape_html(res.detected_lon_col)}</code>",
    ]

    if res.detected_height_col:
        lines.append(f" • Height: <code>{escape_html(res.detected_height_col)}</code>")

    lines.extend([
        "",
        "<i>Your converted dataset is attached below 👇</i>",
    ])
    return "\n".join(lines)


def format_welcome_message() -> str:
    """Generate welcome message for /start."""
    return (
        "👋 <b>Welcome to KB-Geoid Bot!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "I calculate <b>EGM2008 Geoid Undulations (N)</b> and convert:\n"
        " • <b>UTM ➔ Lat/Long & Ellipsoidal Height</b>\n"
        " • <b>MSL Height ➔ Ellipsoidal Height (h = H + N)</b>\n"
        " • <b>Ellipsoidal Height ➔ MSL Height (H = h - N)</b>\n\n"
        "🚀 <b>Quick Input Examples:</b>\n"
        " 🗺️ <b>UTM Zone 48N:</b> <code>48N 593596.681 1224909.7 5.129m</code>\n"
        " 🗺️ <b>UTM Zone 48S:</b> <code>48S 702315 9317050 50</code>\n"
        " 📍 <b>DD:</b> <code>-6.175392, 106.827153, 50</code>\n"
        " 📍 <b>DMS:</b> <code>6°10'31.4\"S 106°49'37.8\"E</code>\n"
        " 📍 <b>GPS Pin:</b> Tap 📎 and share your live location\n"
        " 📁 <b>CSV/Excel:</b> Upload file for batch conversion\n"
    )


def format_utm_guide() -> str:
    """Generate dedicated UTM input guide."""
    return (
        "🗺️ <b>UTM ➔ Lat/Long & Ellipsoidal Height Guide</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "Send your UTM coordinates and MSL elevation to get:\n"
        " 1. <b>Latitude & Longitude (Decimal Degrees & DMS)</b>\n"
        " 2. <b>EGM2008 Geoid Undulation (N)</b>\n"
        " 3. <b>Calculated WGS84 Ellipsoidal Height (h = H + N)</b>\n\n"
        "📌 <b>Format:</b>\n"
        "<code>[Zone] [Easting] [Northing] [Elevation/MSL]</code>\n\n"
        "📌 <b>Examples:</b>\n"
        " • <code>48N 593596.681 1224909.7 5.129m</code> <i>(Zone 48 North, MSL 5.129m)</i>\n"
        " • <code>Zone 48N 593596.681 1224909.7 msl=5.129m</code>\n"
        " • <code>48S 702315 9317050 50</code> <i>(Zone 48 South, MSL 50m)</i>\n"
        " • <code>Zone 48S Easting 702315 Northing 9317050 Elevation 50m</code>\n\n"
        "💡 <i>Try sending <code>48N 593596.681 1224909.7 5.129m</code> right now!</i>"
    )


def format_help_message() -> str:
    """Generate coordinate formatting guide."""
    return (
        "📖 <b>Supported Coordinate Formats & Guide</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "You can send coordinates directly in any of the following formats:\n\n"
        "🗺️ <b>1. Universal Transverse Mercator (UTM):</b>\n"
        " • <code>48N 593596.681 1224909.7 5.129m</code> <i>(Zone 48N with MSL height)</i>\n"
        " • <code>48S 702315 9317050 50</code> <i>(Zone 48S with MSL height)</i>\n"
        " • <code>Zone 48N Easting 593596.681 Northing 1224909.7</code>\n\n"
        "📍 <b>2. Decimal Degrees (DD):</b>\n"
        " • <code>-6.175392, 106.827153, 50</code>\n"
        " • <code>-6.175392, 106.827153</code>\n\n"
        "📍 <b>3. Degrees Minutes Seconds (DMS):</b>\n"
        " • <code>6°10'31.4\"S 106°49'37.8\"E</code>\n"
        " • <code>06 10 31.4 S, 106 49 37.8 E</code>\n\n"
        "📁 <b>Batch CSV/Excel Files:</b>\n"
        "Upload a file with columns for <code>easting</code> / <code>northing</code> / <code>zone</code> or <code>lat</code> / <code>lon</code>."
    )


def format_about_message() -> str:
    """Generate geodetic information about EGM2008."""
    return (
        "ℹ️ <b>About EGM2008 & Geodesy</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "<b>Earth Gravitational Model 2008 (EGM2008)</b> is the official global gravitational model "
        "developed by the National Geospatial-Intelligence Agency (NGA).\n\n"
        "📐 <b>Fundamental Geodesy Formula:</b>\n"
        "<code>h = H + N</code>\n"
        "<code>H = h - N</code>\n\n"
        "Where:\n"
        " • <b>h</b> = Ellipsoidal Height (GPS/GNSS raw height)\n"
        " • <b>H</b> = Orthometric Height (Elevation above MSL)\n"
        " • <b>N</b> = Geoid Undulation (Geoid separation above WGS84)\n\n"
        "⚙️ <b>Grid Resolution:</b> 2.5 arc-minutes (~4.5 km global grid)\n"
        "🎯 <b>Accuracy:</b> Global centimeter-level precision\n"
    )
