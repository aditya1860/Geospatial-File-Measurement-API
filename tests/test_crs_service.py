import math
import pyproj
from shapely.geometry import Polygon, Point, LineString
from app.services.crs_service import CRSService

def test_utm_epsg_calculation():
    # Bangalore, India (lat 12.97, lon 77.59) -> Zone 43 North -> EPSG:32643
    epsg_bangalore = CRSService.get_utm_epsg_for_latlon(12.97, 77.59)
    assert epsg_bangalore == 32643

    # San Francisco, USA (lat 37.77, lon -122.41) -> Zone 10 North -> EPSG:32610
    epsg_sf = CRSService.get_utm_epsg_for_latlon(37.77, -122.41)
    assert epsg_sf == 32610

    # Sydney, Australia (lat -33.86, lon 151.20) -> Zone 56 South -> EPSG:32756
    epsg_sydney = CRSService.get_utm_epsg_for_latlon(-33.86, 151.20)
    assert epsg_sydney == 32756

    # North Pole area (> 84 N) -> UPS North (EPSG:32661)
    epsg_north_pole = CRSService.get_utm_epsg_for_latlon(85.0, 10.0)
    assert epsg_north_pole == 32661

def test_transform_geometry_to_projected():
    # Square in EPSG:4326 near equator/UTM zone 43
    poly_4326 = Polygon([
        (77.0, 10.0),
        (77.01, 10.0),
        (77.01, 10.01),
        (77.0, 10.01),
        (77.0, 10.0)
    ])
    src_crs = pyproj.CRS.from_epsg(4326)

    # Transform
    proj_geom, target_crs = CRSService.transform_geometry_to_projected(poly_4326, src_crs)
    
    assert target_crs.is_projected
    # Expected area should be non-zero and around ~1.2 km^2 (approx 1,000,000 to 1,500,000 m²)
    area = proj_geom.area
    assert 1_000_000 < area < 1_500_000
    assert area != poly_4326.area  # poly_4326.area would be 0.0001 deg^2
