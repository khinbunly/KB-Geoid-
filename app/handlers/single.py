"""Handlers for Single Point coordinate text input and calculations."""

from telegram import Update
from telegram.ext import ContextTypes
from app.engine.converter import ConversionMode, geoid_converter
from app.engine.coordinates import CoordinateParser
from app.ui.formatters import format_point_result
from app.ui.keyboards import get_quick_actions_keyboard
from app.utils.logger import logger
from app.utils.validators import validate_coordinates, validate_height


async def single_point_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle free-text coordinate input from user."""
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()
    
    # Ignore commands (e.g. /start)
    if text.startswith("/"):
        return

    user_mode_str = context.user_data.get("mode", ConversionMode.UNDULATION_ONLY.value)
    
    try:
        # Parse coordinate string
        parsed = CoordinateParser.parse(text)
        lat, lon = validate_coordinates(parsed.lat, parsed.lon)

        # Determine conversion mode
        if parsed.height_type == "msl":
            mode = ConversionMode.MSL_TO_ELLIPSOID
        elif parsed.height_type == "ellipsoid":
            mode = ConversionMode.ELLIPSOID_TO_MSL
        elif parsed.height is not None and user_mode_str in [
            ConversionMode.MSL_TO_ELLIPSOID.value,
            ConversionMode.ELLIPSOID_TO_MSL.value,
        ]:
            mode = ConversionMode(user_mode_str)
        elif parsed.height is not None:
            # Default to MSL -> Ellipsoid if height is supplied but no mode specified
            mode = ConversionMode.MSL_TO_ELLIPSOID
        else:
            mode = ConversionMode.UNDULATION_ONLY

        height_val = None
        if parsed.height is not None and mode != ConversionMode.UNDULATION_ONLY:
            height_val = validate_height(parsed.height)

        # Calculate result
        result = geoid_converter.convert_point(
            lat=lat,
            lon=lon,
            mode=mode,
            input_height=height_val,
        )

        response_html = format_point_result(result, parsed)
        await update.message.reply_html(
            response_html,
            reply_markup=get_quick_actions_keyboard(mode.value),
        )

    except Exception as e:
        logger.info(f"Failed to parse or calculate coordinate '{text}': {e}")
        error_msg = (
            f"⚠️ <b>Coordinate Input Error:</b>\n\n"
            f"{str(e)}\n\n"
            f"💡 <i>Tip: Try sending coordinates like:</i>\n"
            f"• <code>48N 593596.681 1224909.7 5.129m</code>\n"
            f"• <code>48S 702315 9317050 50m</code>\n"
            f"• <code>-6.175392, 106.827153, 50</code>\n"
            f"• <code>6°10'31.4\"S 106°49'37.8\"E</code>"
        )
        await update.message.reply_html(error_msg)


# Optional wizard handler (kept for extensibility)
single_wizard_handler = single_point_handler
