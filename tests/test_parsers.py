import zipfile
from pathlib import Path
from app.services.parser_service import ParserService

def test_shapefile_parser(sample_zip_path, tmp_path):
    # Extract zip
    with zipfile.ZipFile(sample_zip_path, 'r') as z:
        z.extractall(tmp_path)
    
    shp_file = next(tmp_path.glob("*.shp"))
    features, crs = ParserService.parse_shapefile(shp_file)
    
    assert len(features) == 2
    assert features[0].geometry_type == "Polygon"
    assert features[0].properties["NAME"] == "Commercial Complex Block A"
    assert features[0].geometry is not None

def test_kml_parser(sample_kml_path):
    features, crs = ParserService.parse_kml(sample_kml_path)
    
    assert len(features) == 4
    geom_types = [f.geometry_type for f in features]
    assert "Polygon" in geom_types
    assert "LineString" in geom_types
    assert "Point" in geom_types
