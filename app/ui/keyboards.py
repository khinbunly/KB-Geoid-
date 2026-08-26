"""Telegram Inline Keyboard layouts and builders."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from app.engine.converter import ConversionMode


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Generate the primary interactive menu keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("📍 Single Point Calc", callback_data="menu_single"),
            InlineKeyboardButton("🧭 UTM ➔ Lat/Lon & Ellipsoid", callback_data="menu_utm"),
        ],
        [
            InlineKeyboardButton("📁 Batch File (CSV/Excel)", callback_data="menu_batch"),
            InlineKeyboardButton("🔄 Change Calc Mode", callback_data="menu_modes"),
        ],
        [
            InlineKeyboardButton("📖 Formats & Guide", callback_data="menu_help"),
            InlineKeyboardButton("ℹ️ About EGM2008", callback_data="menu_about"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_mode_selector_keyboard(current_mode: str = "") -> InlineKeyboardMarkup:
    """Keyboard to select calculation mode."""
    modes = [
        ("🎯 Undulation Only (N)", ConversionMode.UNDULATION_ONLY.value),
        ("🔺 MSL ➔ Ellipsoid (h = H + N)", ConversionMode.MSL_TO_ELLIPSOID.value),
        ("🔻 Ellipsoid ➔ MSL (H = h - N)", ConversionMode.ELLIPSOID_TO_MSL.value),
    ]

    keyboard = []
    for label, val in modes:
        prefix = "✅ " if val == current_mode else ""
        keyboard.append([InlineKeyboardButton(f"{prefix}{label}", callback_data=f"set_mode_{val}")])

    keyboard.append([InlineKeyboardButton("🔙 Back to Main Menu", callback_data="menu_main")])
    return InlineKeyboardMarkup(keyboard)


def get_quick_actions_keyboard(current_mode: str = "") -> InlineKeyboardMarkup:
    """Quick action buttons after calculation result."""
    keyboard = [
        [
            InlineKeyboardButton("🔄 Switch Mode", callback_data="menu_modes"),
            InlineKeyboardButton("📍 New Point", callback_data="menu_single"),
        ],
        [
            InlineKeyboardButton("📁 Batch Upload", callback_data="menu_batch"),
            InlineKeyboardButton("🏠 Main Menu", callback_data="menu_main"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Single cancel / back button."""
    keyboard = [[InlineKeyboardButton("❌ Cancel / Main Menu", callback_data="menu_main")]]
    return InlineKeyboardMarkup(keyboard)
