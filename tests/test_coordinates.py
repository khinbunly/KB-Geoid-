"""Unit tests for coordinate parsing, format detection, and validation."""

import pytest
from app.engine.coordinates import CoordinateParser
from app.utils.validators import validate_coordinates, validate_height, ValidationError


def test_parse_decimal_degrees():
    """Test parsing standard Decimal Degrees."""
    coord = CoordinateParser.parse("-6.175392, 106.827153")
    assert coord.lat == -6.175392
    assert coord.lon == 106.827153
    assert coord.height is None
    assert coord.coord_format == "Decimal Degrees"


def test_parse_decimal_degrees_with_height():
    """Test parsing DD with height value."""
    coord = CoordinateParser.parse("-6.175392 106.827153 100.5")
    assert coord.lat == -6.175392
    assert coord.lon == 106.827153
    assert coord.height == 100.5


def test_parse_dms():
    """Test parsing Degrees Minutes Seconds format."""
    coord = CoordinateParser.parse('6°10\'31.41"S, 106°49\'37.75"E')
    assert pytest.approx(coord.lat, abs=1e-4) == -6.175392
    assert pytest.approx(coord.lon, abs=1e-4) == 106.827153
    assert coord.coord_format == "DMS"


def test_parse_utm_standard():
    """Test parsing UTM standard: 48S 702315 9317050."""
    coord = CoordinateParser.parse("48S 702315 9317050")
    assert coord.coord_format == "UTM"
    assert coord.utm_zone == "48S"
    assert pytest.approx(coord.lat, abs=0.01) == -6.175
    assert pytest.approx(coord.lon, abs=0.01) == 106.827


def test_parse_utm_with_lat_band_and_height():
    """Test parsing UTM with M band (South) and height: 48M 702315 9317050 50.5."""
    coord = CoordinateParser.parse("48M 702315 9317050 50.5")
    assert coord.coord_format == "UTM"
    assert coord.height == 50.5
    assert pytest.approx(coord.lat, abs=0.01) == -6.175
    assert pytest.approx(coord.lon, abs=0.01) == 106.827


def test_parse_utm_user_input_with_unit():
    """Test parsing exact user input: 48M 593596.681 1224909.7 5.129m."""
    coord = CoordinateParser.parse("48M 593596.681 1224909.7 5.129m")
    assert coord.coord_format == "UTM"
    assert coord.height == 5.129
    assert coord.utm_easting == 593596.681
    assert coord.utm_northing == 1224909.7
    assert pytest.approx(coord.lat, abs=0.01) == 11.08
    assert pytest.approx(coord.lon, abs=0.01) == 105.86


def test_parse_utm_with_key_values():
    """Test parsing UTM key-value format: Zone=48S, Easting=702315, Northing=9317050."""
    coord = CoordinateParser.parse("Zone=48S, Easting=702315, Northing=9317050")
    assert coord.coord_format == "UTM"
    assert pytest.approx(coord.lat, abs=0.01) == -6.175
    assert pytest.approx(coord.lon, abs=0.01) == 106.827


def test_parse_utm_suffix_format():
    """Test parsing UTM suffix format: 702315 9317050 48S."""
    coord = CoordinateParser.parse("702315 9317050 48S")
    assert coord.coord_format == "UTM"
    assert pytest.approx(coord.lat, abs=0.01) == -6.175
    assert pytest.approx(coord.lon, abs=0.01) == 106.827


def test_format_dms_and_utm_conversions():
    """Test converting DD to DMS and UTM strings."""
    dms_str = CoordinateParser.format_dms(-6.175392, 106.827153)
    assert "S" in dms_str
    assert "E" in dms_str
    assert "06°10'" in dms_str

    utm_str = CoordinateParser.to_utm(-6.175392, 106.827153)
    assert "48S" in utm_str


def test_coordinate_validation():
    """Test boundary validation rules."""
    # Valid
    lat, lon = validate_coordinates(-6.0, 106.0)
    assert lat == -6.0 and lon == 106.0

    # Invalid latitude
    with pytest.raises(ValidationError):
        validate_coordinates(95.0, 10.0)

    with pytest.raises(ValidationError):
        validate_coordinates(-90.1, 10.0)

    # Invalid height
    with pytest.raises(ValidationError):
        validate_height(15000.0)

    with pytest.raises(ValidationError):
        validate_height(-1000.0)
