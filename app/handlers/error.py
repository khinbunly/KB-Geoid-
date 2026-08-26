"""Centralized error handling middleware for Telegram Bot."""

import html
import json
import traceback
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from app.utils.logger import logger


async def global_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log uncaught exceptions and alert user gracefully."""
    logger.error("Exception while handling an update:", exc_info=context.error)

    # Format traceback for internal logging
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)

    update_str = update.to_dict() if isinstance(update, Update) else str(update)
    logger.error(f"Update causing error: {json.dumps(update_str, indent=2, default=str)}")

    # Send user friendly notification
    user_message = (
        "⚠️ <b>An unexpected error occurred while processing your request.</b>\n\n"
        "Please check your input formatting or try again with /start."
    )

    try:
        if isinstance(update, Update):
            if update.effective_message:
                await update.effective_message.reply_html(user_message)
            elif update.callback_query:
                await update.callback_query.answer("⚠️ An error occurred. Please try again.")
    except Exception as send_err:
        logger.error(f"Failed to send error message to user: {send_err}")
