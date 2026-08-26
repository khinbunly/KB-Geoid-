"""Telegram Bot Handlers."""

from app.handlers.start import (
    start_handler,
    help_handler,
    about_handler,
    utm_guide_handler,
    menu_callback_handler,
)
from app.handlers.single import single_point_handler, single_wizard_handler
from app.handlers.location import location_handler
from app.handlers.file import document_handler
from app.handlers.error import global_error_handler

__all__ = [
    "start_handler",
    "help_handler",
    "about_handler",
    "utm_guide_handler",
    "menu_callback_handler",
    "single_point_handler",
    "single_wizard_handler",
    "location_handler",
    "document_handler",
    "global_error_handler",
]
