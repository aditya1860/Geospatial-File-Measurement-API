import os
import zipfile
from pathlib import Path
import shapefile

def generate_sample_shapefile_zip(output_zip: Path):
    """
    Generates a zip file containing a complete Shapefile (.shp, .shx, .dbf, .prj)
    with Polygon, LineString, and Point records in EPSG:4326.
    """
    temp_dir = output_zip.parent / "temp_shp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    shp_base = temp_dir / "parcels_and_roads"

    # 1. Create Polygon Shapefile (e.g. Agricultural Parcels / Land Parcels in San Francisco / Bangalore)
    # Let's create a polygon shapefile
    w = shapefile.Writer(str(shp_base), shapeType=shapefile.POLYGON)
    w.field("NAME", "C", size=50)
    w.field("CATEGORY", "C", size=30)
    w.field("ZONE_CODE", "C", size=10)

    # Feature 1: Central Park / Agricultural plot (lat: 12.97, lon: 77.59)
    w.poly([
        [
            [77.5900, 12.9700],
            [77.5950, 12.9700],
            [77.5950, 12.9750],
            [77.5900, 12.9750],
            [77.5900, 12.9700]
        ]
    ])
    w.record(NAME="Commercial Complex Block A", CATEGORY="Commercial", ZONE_CODE="CC-01")

    # Feature 2: Triangular parcel
    w.poly([
        [
            [77.6000, 12.9800],
            [77.6100, 12.9800],
            [77.6050, 12.9900],
            [77.6000, 12.9800]
        ]
    ])
    w.record(NAME="Green Belt Reserve Sector 4", CATEGORY="Park/Reserve", ZONE_CODE="GB-04")

    w.close()

    # 2. Write PRJ file (EPSG:4326 WKT)
    wkt_4326 = (
        'GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137,298.257223563]],'
        'PRIMEM["Greenwich",0],UNIT["Degree",0.017453292519943295]]'
    )
    prj_file = shp_base.with_suffix(".prj")
    prj_file.write_text(wkt_4326, encoding="utf-8")

    # 3. Package into ZIP
    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as z:
        for ext in [".shp", ".shx", ".dbf", ".prj"]:
            f = shp_base.with_suffix(ext)
            if f.exists():
                z.write(f, arcname=f.name)
                f.unlink()
    
    if temp_dir.exists():
        temp_dir.rmdir()
    print(f"Generated sample Shapefile ZIP: {output_zip}")

def generate_sample_kml(output_kml: Path):
    """
    Generates a rich KML file containing Polygons, LineStrings, and Points.
    """
    kml_content = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Metropolitan Infrastructure &amp; Survey</name>
    <description>Sample dataset with agricultural plots, highways, and sensor stations.</description>
    
    <!-- 1. Polygon: Agricultural Plot -->
    <Placemark>
      <name>High-Tech Agricultural Field Alpha</name>
      <description>Precision agriculture test field</description>
      <ExtendedData>
        <Data name="CropType"><value>Organic Wheat</value></Data>
        <Data name="IrrigationSystem"><value>Drip Automated</value></Data>
      </ExtendedData>
      <Polygon>
        <outerBoundaryIs>
          <LinearRing>
            <coordinates>
              -122.084,37.422,0
              -122.080,37.422,0
              -122.080,37.426,0
              -122.084,37.426,0
              -122.084,37.422,0
            </coordinates>
          </LinearRing>
        </outerBoundaryIs>
      </Polygon>
    </Placemark>

    <!-- 2. LineString: Highway Transit Corridor -->
    <Placemark>
      <name>Corridor Express Highway Link</name>
      <description>Major highway connecting industrial zone</description>
      <ExtendedData>
        <Data name="LaneCount"><value>4</value></Data>
        <Data name="SurfaceType"><value>Asphalt Concrete</value></Data>
      </ExtendedData>
      <LineString>
        <coordinates>
          -122.084,37.420,0
          -122.075,37.424,0
          -122.065,37.428,0
          -122.050,37.435,0
        </coordinates>
      </LineString>
    </Placemark>

    <!-- 3. Point: Weather & Environmental Sensor -->
    <Placemark>
      <name>Weather Sensor Station 01</name>
      <description>IoT telemetry node</description>
      <ExtendedData>
        <Data name="SensorType"><value>Anemometer + Barometer</value></Data>
        <Data name="BatteryLevel"><value>98%</value></Data>
      </ExtendedData>
      <Point>
        <coordinates>-122.082,37.423,0</coordinates>
      </Point>
    </Placemark>

    <!-- 4. Polygon: Irregular lake boundary with inner hole -->
    <Placemark>
      <name>Freshwater Reservoir Lake</name>
      <description>Municipal water catchment area</description>
      <Polygon>
        <outerBoundaryIs>
          <LinearRing>
            <coordinates>
              -122.090,37.430,0
              -122.070,37.430,0
              -122.070,37.440,0
              -122.090,37.440,0
              -122.090,37.430,0
            </coordinates>
          </LinearRing>
        </outerBoundaryIs>
        <innerBoundaryIs>
          <LinearRing>
            <coordinates>
              -122.082,37.433,0
              -122.078,37.433,0
              -122.078,37.437,0
              -122.082,37.437,0
              -122.082,37.433,0
            </coordinates>
          </LinearRing>
        </innerBoundaryIs>
      </Polygon>
    </Placemark>
  </Document>
</kml>
"""
    output_kml.write_text(kml_content, encoding="utf-8")
    print(f"Generated sample KML: {output_kml}")

if __name__ == "__main__":
    samples_dir = Path(__file__).resolve().parent
    samples_dir.mkdir(parents=True, exist_ok=True)
    generate_sample_shapefile_zip(samples_dir / "sample_parcels.zip")
    generate_sample_kml(samples_dir / "sample_infrastructure.kml")
