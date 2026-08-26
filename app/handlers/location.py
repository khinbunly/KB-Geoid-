"""Handler for native Telegram GPS Location pins."""

from telegram import Update
from telegram.ext import ContextTypes
from app.engine.converter import ConversionMode, geoid_converter
from app.engine.coordinates import ParsedCoordinate
from app.ui.formatters import format_point_result
from app.ui.keyboards import get_quick_actions_keyboard
from app.utils.logger import logger
from app.utils.validators import validate_coordinates


async def location_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process incoming GPS location pin from user."""
    if not update.message or not update.message.location:
        return

    loc = update.message.location
    lat = float(loc.latitude)
    lon = float(loc.longitude)

    logger.info(f"Received GPS location pin: ({lat}, {lon})")

    try:
        lat, lon = validate_coordinates(lat, lon)
        user_mode_str = context.user_data.get("mode", ConversionMode.UNDULATION_ONLY.value)
        mode = ConversionMode(user_mode_str)

        parsed = ParsedCoordinate(
            lat=round(lat, 7),
            lon=round(lon, 7),
            coord_format="GPS Location Pin",
        )

        result = geoid_converter.convert_point(
            lat=lat,
            lon=lon,
            mode=ConversionMode.UNDULATION_ONLY,
        )

        response_html = format_point_result(result, parsed)
        await update.message.reply_html(
            response_html,
            reply_markup=get_quick_actions_keyboard(mode.value),
        )

    except Exception as e:
        logger.error(f"Error processing GPS location pin: {e}")
        await update.message.reply_html(
            f"❌ <b>Error processing location:</b> {str(e)}"
        )
