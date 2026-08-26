"""Command handlers for /start, /help, /about, /utm and menu callbacks."""

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from app.engine.converter import ConversionMode
from app.ui.keyboards import (
    get_main_menu_keyboard,
    get_mode_selector_keyboard,
    get_cancel_keyboard,
)
from app.ui.formatters import (
    format_welcome_message,
    format_help_message,
    format_about_message,
    format_utm_guide,
)
from app.utils.logger import logger


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    if "mode" not in context.user_data:
        context.user_data["mode"] = ConversionMode.UNDULATION_ONLY.value

    msg = format_welcome_message()
    reply_markup = get_main_menu_keyboard()

    if update.message:
        await update.message.reply_html(msg, reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            msg, reply_markup=reply_markup, parse_mode=ParseMode.HTML
        )


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    msg = format_help_message()
    reply_markup = get_main_menu_keyboard()

    if update.message:
        await update.message.reply_html(msg, reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            msg, reply_markup=reply_markup, parse_mode=ParseMode.HTML
        )


async def utm_guide_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /utm command."""
    msg = format_utm_guide()
    reply_markup = get_cancel_keyboard()

    if update.message:
        await update.message.reply_html(msg, reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            msg, reply_markup=reply_markup, parse_mode=ParseMode.HTML
        )


async def about_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /about command."""
    msg = format_about_message()
    reply_markup = get_main_menu_keyboard()

    if update.message:
        await update.message.reply_html(msg, reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            msg, reply_markup=reply_markup, parse_mode=ParseMode.HTML
        )


async def menu_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle navigation callback queries from inline buttons."""
    query = update.callback_query
    if not query:
        return
    await query.answer()
    data = query.data

    current_mode = context.user_data.get("mode", ConversionMode.UNDULATION_ONLY.value)

    if data == "menu_main":
        await query.edit_message_text(
            format_welcome_message(),
            reply_markup=get_main_menu_keyboard(),
            parse_mode=ParseMode.HTML,
        )

    elif data == "menu_utm":
        await query.edit_message_text(
            format_utm_guide(),
            reply_markup=get_cancel_keyboard(),
            parse_mode=ParseMode.HTML,
        )

    elif data == "menu_modes":
        msg = (
            "⚙️ <b>Select Calculation Mode:</b>\n\n"
            "• <b>Undulation Only (N):</b> Computes geoid separation $N$.\n"
            "• <b>MSL ➔ Ellipsoid:</b> Converts orthometric height to ellipsoidal ($h = H + N$).\n"
            "• <b>Ellipsoid ➔ MSL:</b> Converts GPS ellipsoidal height to MSL ($H = h - N$)."
        )
        await query.edit_message_text(
            msg,
            reply_markup=get_mode_selector_keyboard(current_mode),
            parse_mode=ParseMode.HTML,
        )

    elif data.startswith("set_mode_"):
        new_mode = data.replace("set_mode_", "")
        context.user_data["mode"] = new_mode
        msg = (
            f"✅ <b>Mode updated!</b>\n\n"
            f"Current active mode: <code>{new_mode}</code>\n"
            f"Send coordinates now (DD, DMS, or UTM) or return to main menu."
        )
        await query.edit_message_text(
            msg,
            reply_markup=get_mode_selector_keyboard(new_mode),
            parse_mode=ParseMode.HTML,
        )

    elif data == "menu_single":
        msg = (
            "📍 <b>Single Point Calculation</b>\n\n"
            "Please send coordinates in any format:\n"
            " • <b>UTM Zone 48N:</b> <code>48N 593596.681 1224909.7 5.129m</code>\n"
            " • <b>UTM Zone 48S:</b> <code>48S 702315 9317050 50</code>\n"
            " • <b>DD:</b> <code>-6.175392, 106.827153</code>\n"
            " • <b>DD with Height:</b> <code>-6.175392, 106.827153, 100</code>\n"
            " • <b>DMS:</b> <code>6°10'31.4\"S 106°49'37.8\"E</code>\n\n"
            "Or simply share your <b>Live GPS Location Pin</b> 📍"
        )
        await query.edit_message_text(
            msg,
            reply_markup=get_cancel_keyboard(),
            parse_mode=ParseMode.HTML,
        )

    elif data == "menu_batch":
        msg = (
            "📁 <b>Batch CSV / Excel Conversion</b>\n\n"
            "Upload any <code>.csv</code>, <code>.tsv</code>, or <code>.xlsx</code> file.\n"
            "The table can contain columns for:\n"
            " • <b>UTM</b> (e.g. <code>easting</code>, <code>northing</code>, <code>zone</code>)\n"
            " • <b>Lat & Lon</b> (e.g. <code>lat</code>, <code>lon</code>)\n"
            " • <b>Height</b> (optional, e.g. <code>height</code>, <code>elevation</code>)\n\n"
            "The bot will calculate undulations and conversions for all rows."
        )
        await query.edit_message_text(
            msg,
            reply_markup=get_cancel_keyboard(),
            parse_mode=ParseMode.HTML,
        )

    elif data == "menu_help":
        await query.edit_message_text(
            format_help_message(),
            reply_markup=get_main_menu_keyboard(),
            parse_mode=ParseMode.HTML,
        )

    elif data == "menu_about":
        await query.edit_message_text(
            format_about_message(),
            reply_markup=get_main_menu_keyboard(),
            parse_mode=ParseMode.HTML,
        )
