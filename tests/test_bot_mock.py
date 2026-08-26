"""Unit tests for Telegram Bot UI components and formatters."""

from app.engine.converter import ConversionMode, PointResult
from app.ui.formatters import (
    format_about_message,
    format_help_message,
    format_point_result,
    format_welcome_message,
)
from app.ui.keyboards import (
    get_main_menu_keyboard,
    get_mode_selector_keyboard,
    get_quick_actions_keyboard,
)


def test_ui_keyboards():
    """Verify inline keyboards have correct structure and callbacks."""
    main_kb = get_main_menu_keyboard()
    assert len(main_kb.inline_keyboard) >= 3

    mode_kb = get_mode_selector_keyboard(ConversionMode.MSL_TO_ELLIPSOID.value)
    # Check that checkmark is present on selected mode
    buttons_text = [btn.text for row in mode_kb.inline_keyboard for btn in row]
    assert any("✅" in text for text in buttons_text)

    actions_kb = get_quick_actions_keyboard()
    assert len(actions_kb.inline_keyboard) == 2


def test_ui_formatters():
    """Verify HTML message formatting produces valid strings without errors."""
    welcome = format_welcome_message()
    assert "KB-Geoid" in welcome
    assert "EGM2008" in welcome

    help_msg = format_help_message()
    assert "Decimal Degrees" in help_msg
    assert "DMS" in help_msg
    assert "UTM" in help_msg

    about_msg = format_about_message()
    assert "h = H + N" in about_msg

    # Point result formatting
    res = PointResult(
        lat=-6.175392,
        lon=106.827153,
        mode=ConversionMode.MSL_TO_ELLIPSOID,
        input_height=100.0,
        output_height=117.9371,
        geoid_undulation_n=17.9371,
        ellipsoidal_height_h=117.9371,
        orthometric_height_H=100.0,
    )
    res_card = format_point_result(res)
    assert "Geoid Undulation (N):" in res_card
    assert "+17.9371 m" in res_card
    assert "117.9371 m" in res_card
