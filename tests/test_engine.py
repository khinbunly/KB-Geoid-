"""Accuracy and validation unit tests for EGM2008 Geoid Engine."""

import math
import numpy as np
import pytest
from app.engine.converter import ConversionMode, geoid_converter
from app.engine.geoid import geoid_engine


# Official EGM2008 Reference benchmark test points (Lat, Lon, Exact N value in meters)
BENCHMARKS = [
    # Jakarta (Monas), Indonesia
    (-6.175392, 106.827153, 17.937, 0.01),
    # Greenwich Observatory, UK
    (51.4769, 0.0005, 45.893, 0.01),
    # Mount Everest, Nepal/China
    (27.9881, 86.9250, -28.427, 0.01),
    # Death Valley (Badwater), USA
    (36.2419, -116.8258, -29.869, 0.01),
    # Sydney Opera House, Australia
    (-33.8568, 151.2153, 22.394, 0.01),
    # Prime Meridian / Equator intersection
    (0.0, 0.0, 17.225, 0.01),
]


def test_egm2008_engine_initialization():
    """Verify EGM2008 engine is initialized and reports metadata."""
    info = geoid_engine.info()
    assert "EGM2008" in info["model"]
    assert "backend" in info
    assert info["crs_ellipsoidal"] == "EPSG:4979 (WGS84 3D)"


@pytest.mark.parametrize("lat, lon, expected_n, tolerance", BENCHMARKS)
def test_egm2008_benchmark_points(lat, lon, expected_n, tolerance):
    """Verify geoid undulation against official global EGM2008 benchmark points."""
    n = geoid_engine.get_undulation(lat, lon)
    assert math.isclose(n, expected_n, abs_tol=tolerance), (
        f"Geoid undulation at ({lat}, {lon}) was {n:.4f}m, expected ~{expected_n:.4f}m"
    )


def test_height_conversion_bidirectional_consistency():
    """Verify that converting MSL -> Ellipsoid -> MSL has zero round-trip loss."""
    lat, lon = -6.175392, 106.827153
    original_msl = 125.4500

    # MSL to Ellipsoid: h = H + N
    h_res = geoid_converter.convert_point(
        lat=lat, lon=lon, mode=ConversionMode.MSL_TO_ELLIPSOID, input_height=original_msl
    )
    ellipsoid_height = h_res.ellipsoidal_height_h
    n = h_res.geoid_undulation_n

    assert math.isclose(ellipsoid_height, original_msl + n, abs_tol=1e-6)

    # Ellipsoid to MSL: H = h - N
    msl_res = geoid_converter.convert_point(
        lat=lat, lon=lon, mode=ConversionMode.ELLIPSOID_TO_MSL, input_height=ellipsoid_height
    )
    reconstructed_msl = msl_res.orthometric_height_H

    assert math.isclose(reconstructed_msl, original_msl, abs_tol=1e-6)


def test_vectorized_batch_accuracy():
    """Verify that vectorized numpy array batch matches scalar calculations."""
    lats = [-6.175392, 51.4769, 27.9881, 36.2419, -33.8568]
    lons = [106.827153, 0.0005, 86.9250, -116.8258, 151.2153]

    scalar_results = [geoid_engine.get_undulation(la, lo) for la, lo in zip(lats, lons)]
    batch_results = geoid_engine.get_undulations_batch(lats, lons)

    np.testing.assert_allclose(batch_results, scalar_results, atol=1e-5)


def test_boundary_coordinates():
    """Verify engine handles poles and antimeridian cleanly without crashing."""
    # North Pole
    n_north = geoid_engine.get_undulation(90.0, 0.0)
    assert -100.0 < n_north < 100.0

    # South Pole
    n_south = geoid_engine.get_undulation(-90.0, 0.0)
    assert -100.0 < n_south < 100.0

    # Antimeridian (+180 and -180 should match)
    n_pos180 = geoid_engine.get_undulation(0.0, 180.0)
    n_neg180 = geoid_engine.get_undulation(0.0, -180.0)
    assert math.isclose(n_pos180, n_neg180, abs_tol=1e-4)
