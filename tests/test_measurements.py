import pyproj
from shapely.geometry import Polygon, LineString, Point
from app.services.measurement_service import MeasurementService
from app.services.parser_service import ParsedFeature

def test_polygon_measurement():
    # Square polygon in San Francisco
    poly = Polygon([
        [-122.084, 37.422],
        [-122.080, 37.422],
        [-122.080, 37.426],
        [-122.084, 37.426],
        [-122.084, 37.422]
    ])
    feature = ParsedFeature(
        feature_id="poly-1",
        geometry=poly,
        geometry_type="Polygon",
        properties={"land_use": "residential"},
        crs=pyproj.CRS.from_epsg(4326)
    )

    meas = MeasurementService.calculate_feature_measurement(feature)
    
    assert meas.status == "SUCCESS"
    assert meas.is_measurable is True
    assert meas.measurements.area is not None
    assert meas.measurements.area.sq_meters > 0
    assert meas.measurements.area.hectares > 0
    assert meas.measurements.perimeter is not None
    assert meas.measurements.perimeter.meters > 0

def test_linestring_measurement():
    line = LineString([
        [-122.084, 37.420],
        [-122.075, 37.424],
        [-122.065, 37.428]
    ])
    feature = ParsedFeature(
        feature_id="line-1",
        geometry=line,
        geometry_type="LineString",
        properties={"road_type": "highway"},
        crs=pyproj.CRS.from_epsg(4326)
    )

    meas = MeasurementService.calculate_feature_measurement(feature)

    assert meas.status == "SUCCESS"
    assert meas.is_measurable is True
    assert meas.measurements.length is not None
    assert meas.measurements.length.meters > 0
    assert meas.measurements.length.kilometers > 0

def test_point_measurement():
    pt = Point([-122.082, 37.423])
    feature = ParsedFeature(
        feature_id="pt-1",
        geometry=pt,
        geometry_type="Point",
        properties={"sensor": "temp"},
        crs=pyproj.CRS.from_epsg(4326)
    )

    meas = MeasurementService.calculate_feature_measurement(feature)

    assert meas.status == "NO_MEASUREMENT_REQUIRED"
    assert meas.is_measurable is False
    assert meas.measurements.area is None
    assert meas.measurements.length is None

def test_unsupported_geometry_graceful_handling():
    feature = ParsedFeature(
        feature_id="null-1",
        geometry=None,
        geometry_type="Unknown",
        properties={},
        crs=pyproj.CRS.from_epsg(4326)
    )

    meas = MeasurementService.calculate_feature_measurement(feature)
    assert meas.status == "SKIPPED"
    assert meas.is_measurable is False
