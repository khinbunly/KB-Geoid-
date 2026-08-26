"""Unit tests for batch CSV and Excel file processing."""

import io
import pandas as pd
import pytest
from app.engine.batch import BatchProcessor
from app.engine.converter import ConversionMode


def test_batch_csv_undulation_processing():
    """Test batch calculation on a simulated CSV file with lat/lon."""
    csv_data = (
        "point_id,latitude,longitude,height\n"
        "PT01,-6.175392,106.827153,50.0\n"
        "PT02,51.4769,0.0005,100.0\n"
        "PT03,27.9881,86.9250,8848.0\n"
    ).encode("utf-8")

    result = BatchProcessor.process_file(
        file_content=csv_data,
        filename="test_points.csv",
        mode=ConversionMode.MSL_TO_ELLIPSOID,
    )

    assert result.total_points == 3
    assert result.detected_lat_col == "latitude"
    assert result.detected_lon_col == "longitude"
    assert result.detected_height_col == "height"
    assert "Geoid_Undulation_N_m" in result.output_filename or result.output_bytes

    out_df = pd.read_csv(io.BytesIO(result.output_bytes))
    assert "Geoid_Undulation_N_m" in out_df.columns
    assert "Ellipsoidal_Height_h_m" in out_df.columns
    assert len(out_df) == 3
    assert pytest.approx(out_df.loc[0, "Geoid_Undulation_N_m"], abs=0.1) == 17.937


def test_batch_utm_csv_processing():
    """Test batch processing on a CSV file containing UTM coordinates."""
    csv_data = (
        "point_id,easting,northing,zone,elevation\n"
        "UTM01,702315,9317050,48S,10.0\n"
        "UTM02,702500,9317200,48S,25.0\n"
    ).encode("utf-8")

    result = BatchProcessor.process_file(
        file_content=csv_data,
        filename="utm_survey.csv",
        mode=ConversionMode.UNDULATION_ONLY,
    )

    assert result.total_points == 2
    out_df = pd.read_csv(io.BytesIO(result.output_bytes))
    assert "Calculated_Lat" in out_df.columns
    assert "Calculated_Lon" in out_df.columns
    assert "Geoid_Undulation_N_m" in out_df.columns
    assert pytest.approx(out_df.loc[0, "Geoid_Undulation_N_m"], abs=0.2) == 17.94


def test_batch_excel_processing():
    """Test batch processing on an in-memory Excel spreadsheet (.xlsx)."""
    df = pd.DataFrame({
        "ID": ["A", "B"],
        "Lat": [-6.2, -6.3],
        "Lon": [106.8, 106.9],
        "MSL_Elev": [10.0, 20.0],
    })

    excel_bio = io.BytesIO()
    with pd.ExcelWriter(excel_bio, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    excel_bytes = excel_bio.getvalue()

    result = BatchProcessor.process_file(
        file_content=excel_bytes,
        filename="survey.xlsx",
        mode=ConversionMode.UNDULATION_ONLY,
    )

    assert result.total_points == 2
    assert result.output_filename.endswith(".xlsx")
    
    out_df = pd.read_excel(io.BytesIO(result.output_bytes))
    assert "Geoid_Undulation_N_m" in out_df.columns
    assert len(out_df) == 2


def test_batch_column_detection():
    """Test smart column detection with various naming schemes."""
    df1 = pd.DataFrame({"y_coord": [1.0], "x_coord": [2.0], "z": [3.0]})
    lat, lon, h, zone = BatchProcessor.detect_columns(df1)
    assert lat == "y_coord" and lon == "x_coord" and h == "z"

    df2 = pd.DataFrame({"Lintang": [1.0], "Bujur": [2.0], "Tinggi": [3.0]})
    lat2, lon2, h2, zone2 = BatchProcessor.detect_columns(df2)
    assert lat2 == "Lintang" and lon2 == "Bujur" and h2 == "Tinggi"

    df3 = pd.DataFrame({"Easting": [702315], "Northing": [9317050], "Zone": ["48S"]})
    north, east, h3, zone3 = BatchProcessor.detect_columns(df3)
    assert north == "Northing" and east == "Easting" and zone3 == "Zone"
