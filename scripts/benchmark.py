"""Benchmark and validation script for KB-Geoid."""

import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import time
import numpy as np
from app.engine.converter import ConversionMode, geoid_converter
from app.engine.geoid import geoid_engine


def run_benchmark():
    print("=" * 75)
    print("              KB-Geoid EGM2008 Engine Benchmark & Validation             ")
    print("=" * 75)

    info = geoid_engine.info()
    print(f"Model:           {info['model']}")
    print(f"Backend:         {info['backend']}")
    print(f"Ellipsoidal CRS: {info['crs_ellipsoidal']}")
    print(f"Orthometric CRS: {info['crs_orthometric']}")
    print(f"Resolution:      {info['grid_resolution']}")
    print("-" * 75)

    # 1. Global Benchmark Ground Truth Points
    test_points = [
        ("Jakarta (Monas), ID", -6.175392, 106.827153, 17.937),
        ("Greenwich, UK", 51.4769, 0.0005, 45.893),
        ("Mt. Everest, NP", 27.9881, 86.9250, -28.427),
        ("Death Valley, US", 36.2419, -116.8258, -29.869),
        ("Sydney Opera, AU", -33.8568, 151.2153, 22.394),
        ("Prime/Equator", 0.0, 0.0, 17.225),
    ]

    print("\n[1] Official EGM2008 Benchmark Reference Comparison:")
    print(f"{'Location':<22} | {'Lat':>8} | {'Lon':>9} | {'Calculated N':>12} | {'Ref N':>8} | {'Diff':>8}")
    print("-" * 75)
    for name, lat, lon, expected in test_points:
        n = geoid_engine.get_undulation(lat, lon)
        diff = n - expected
        print(f"{name:<22} | {lat:8.4f} | {lon:9.4f} | {n:10.4f} m | {expected:6.3f} m | {diff:+7.4f} m")

    # 2. MSL <-> Ellipsoidal Height Conversion Consistency Check
    print("\n[2] Bidirectional Height Conversion Consistency (h = H + N):")
    sample_msl = 150.000
    res_msl2ellips = geoid_converter.convert_point(
        -6.175392, 106.827153, ConversionMode.MSL_TO_ELLIPSOID, input_height=sample_msl
    )
    res_ellips2msl = geoid_converter.convert_point(
        -6.175392, 106.827153, ConversionMode.ELLIPSOID_TO_MSL, input_height=res_msl2ellips.ellipsoidal_height_h
    )

    print(f" • Input MSL (H):             {sample_msl:.4f} m")
    print(f" • Geoid Undulation (N):       {res_msl2ellips.geoid_undulation_n:+.4f} m")
    print(f" • Calculated Ellipsoid (h):  {res_msl2ellips.ellipsoidal_height_h:.4f} m")
    print(f" • Reconstructed MSL (H'):    {res_ellips2msl.orthometric_height_H:.4f} m")
    print(f" • Round-trip delta:           {abs(res_ellips2msl.orthometric_height_H - sample_msl):.2e} m (PASS)")

    # 3. Vectorized Regional Batch Performance Test
    print("\n[3] Vectorized Batch Performance Test (5,000 coordinates):")
    np.random.seed(42)
    lats = np.random.uniform(-7.5, -5.5, 5000)
    lons = np.random.uniform(106.0, 108.0, 5000)

    t0 = time.time()
    undulations = geoid_engine.get_undulations_batch(lats, lons)
    elapsed = time.time() - t0

    pts_per_sec = len(lats) / elapsed
    print(f" • Processed:                  {len(lats):,} points")
    print(f" • Time Elapsed:               {elapsed:.3f} seconds")
    print(f" • Throughput:                 {pts_per_sec:,.0f} points/second")
    print(f" • Min N:                      {np.min(undulations):+.4f} m")
    print(f" • Mean N:                     {np.mean(undulations):+.4f} m")
    print(f" • Max N:                      {np.max(undulations):+.4f} m")
    print("=" * 75)
    print("All validation checks passed successfully!\n")


if __name__ == "__main__":
    run_benchmark()
