import os
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import pyproj
import shapefile
from shapely.geometry import shape as shapely_shape, mapping, Point, LineString, Polygon, MultiPoint, MultiLineString, MultiPolygon
from shapely.geometry.base import BaseGeometry
import xml.etree.ElementTree as ET

from app.schemas.feature import FeatureDetail, GeometrySchema
from app.services.crs_service import CRSService
from app.utils.logger import logger

class ParsedFeature:
    def __init__(
        self,
        feature_id: str,
        geometry: BaseGeometry,
        geometry_type: str,
        properties: Dict[str, Any],
        crs: pyproj.CRS
    ):
        self.feature_id = feature_id
        self.geometry = geometry
        self.geometry_type = geometry_type
        self.properties = properties
        self.crs = crs

    def to_geojson_dict(self) -> Dict[str, Any]:
        return {
            "type": "Feature",
            "id": self.feature_id,
            "geometry": mapping(self.geometry) if self.geometry else None,
            "properties": self.properties
        }

class ParserService:
    @classmethod
    def parse_shapefile(cls, shp_path: Path) -> Tuple[List[ParsedFeature], pyproj.CRS]:
        """
        Parses an ESRI Shapefile using PyShp and Shapely.
        Extracts features, geometry, attributes, and CRS (from .prj).
        """
        base_path = shp_path.with_suffix("")
        prj_path = base_path.with_suffix(".prj")

        # Determine CRS from .prj file if present
        source_crs = pyproj.CRS.from_epsg(4326)
        if prj_path.exists():
            try:
                prj_text = prj_path.read_text(encoding="utf-8", errors="ignore").strip()
                if prj_text:
                    source_crs = CRSService.parse_crs_from_prj_text(prj_text)
            except Exception as e:
                logger.warning(f"Could not read PRJ file {prj_path}: {e}. Defaulting to EPSG:4326.")

        parsed_features: List[ParsedFeature] = []

        try:
            with shapefile.Reader(str(shp_path), encoding="utf-8", encodingErrors="ignore") as sf:
                fields = [f[0] for f in sf.fields[1:]]  # skip DeletionFlag

                for idx, shape_rec in enumerate(sf.shapeRecords()):
                    feature_id = str(idx + 1)
                    raw_shape = shape_rec.shape
                    record = shape_rec.record

                    # Build properties dictionary
                    props: Dict[str, Any] = {}
                    for field_name, value in zip(fields, record):
                        # Convert bytes or date objects to serializable formats
                        if isinstance(value, bytes):
                            try:
                                value = value.decode("utf-8", errors="ignore")
                            except Exception:
                                value = str(value)
                        props[field_name] = value

                    # Construct geometry
                    geom = None
                    geom_type = "Unknown"
                    if raw_shape and raw_shape.shapeTypeName != "NULL":
                        try:
                            geo_interface = raw_shape.__geo_interface__
                            geom = shapely_shape(geo_interface)
                            geom_type = geom.geom_type
                        except Exception as ex:
                            logger.warning(f"Error creating geometry for feature {feature_id}: {ex}")
                            geom_type = raw_shape.shapeTypeName

                    parsed_features.append(
                        ParsedFeature(
                            feature_id=feature_id,
                            geometry=geom,
                            geometry_type=geom_type,
                            properties=props,
                            crs=source_crs
                        )
                    )
        except Exception as e:
            logger.error(f"Failed to read shapefile {shp_path}: {e}")
            raise ValueError(f"Failed to parse shapefile: {str(e)}")

        return parsed_features, source_crs

    @classmethod
    def parse_kml(cls, kml_path: Path) -> Tuple[List[ParsedFeature], pyproj.CRS]:
        """
        Parses a KML file into features using XML parsing and Shapely geometries.
        Standard KML coordinates are strictly EPSG:4326.
        """
        source_crs = pyproj.CRS.from_epsg(4326)
        parsed_features: List[ParsedFeature] = []

        try:
            tree = ET.parse(str(kml_path))
            root = tree.getroot()
            
            # Namespace handling
            ns = ""
            if root.tag.startswith("{"):
                ns = root.tag.split("}")[0] + "}"

            placemarks = root.findall(f".//{ns}Placemark")
            
            for idx, pm in enumerate(placemarks):
                feature_id = str(idx + 1)
                
                # Extract properties
                props: Dict[str, Any] = {}
                name_elem = pm.find(f"{ns}name")
                if name_elem is not None and name_elem.text:
                    props["name"] = name_elem.text.strip()
                    feature_id = props["name"]

                desc_elem = pm.find(f"{ns}description")
                if desc_elem is not None and desc_elem.text:
                    props["description"] = desc_elem.text.strip()

                # ExtendedData
                ext_data = pm.find(f"{ns}ExtendedData")
                if ext_data is not None:
                    for data in ext_data.findall(f"{ns}Data"):
                        name_attr = data.attrib.get("name")
                        val_elem = data.find(f"{ns}value")
                        if name_attr and val_elem is not None and val_elem.text:
                            props[name_attr] = val_elem.text.strip()
                    for sdata in ext_data.findall(f".//{ns}SimpleData"):
                        name_attr = sdata.attrib.get("name")
                        if name_attr and sdata.text:
                            props[name_attr] = sdata.text.strip()

                # Parse Geometry
                geom, geom_type = cls._parse_kml_geometry(pm, ns)

                parsed_features.append(
                    ParsedFeature(
                        feature_id=str(feature_id),
                        geometry=geom,
                        geometry_type=geom_type,
                        properties=props,
                        crs=source_crs
                    )
                )

        except Exception as e:
            logger.error(f"Failed to parse KML file {kml_path}: {e}")
            raise ValueError(f"Failed to parse KML file: {str(e)}")

        return parsed_features, source_crs

    @classmethod
    def _parse_kml_coordinates(cls, coord_str: str) -> List[Tuple[float, float]]:
        """Parses KML coordinate text 'lon,lat,alt lon,lat,alt ...' into list of (lon, lat) tuples."""
        coords = []
        for token in coord_str.strip().split():
            parts = token.split(",")
            if len(parts) >= 2:
                try:
                    lon = float(parts[0])
                    lat = float(parts[1])
                    coords.append((lon, lat))
                except ValueError:
                    continue
        return coords

    @classmethod
    def _parse_kml_geometry(cls, pm_elem: ET.Element, ns: str) -> Tuple[Optional[BaseGeometry], str]:
        """Extracts and builds Shapely geometry from Placemark XML element."""
        # 1. Point
        pt_elem = pm_elem.find(f".//{ns}Point")
        if pt_elem is not None:
            c_elem = pt_elem.find(f"{ns}coordinates")
            if c_elem is not None and c_elem.text:
                coords = cls._parse_kml_coordinates(c_elem.text)
                if coords:
                    return Point(coords[0]), "Point"

        # 2. LineString
        ls_elem = pm_elem.find(f".//{ns}LineString")
        if ls_elem is not None:
            c_elem = ls_elem.find(f"{ns}coordinates")
            if c_elem is not None and c_elem.text:
                coords = cls._parse_kml_coordinates(c_elem.text)
                if len(coords) >= 2:
                    return LineString(coords), "LineString"

        # 3. Polygon
        poly_elem = pm_elem.find(f".//{ns}Polygon")
        if poly_elem is not None:
            outer_elem = poly_elem.find(f".//{ns}outerBoundaryIs//{ns}coordinates")
            if outer_elem is not None and outer_elem.text:
                outer_coords = cls._parse_kml_coordinates(outer_elem.text)
                if len(outer_coords) >= 3:
                    inner_rings = []
                    for inner_elem in poly_elem.findall(f".//{ns}innerBoundaryIs//{ns}coordinates"):
                        if inner_elem.text:
                            in_coords = cls._parse_kml_coordinates(inner_elem.text)
                            if len(in_coords) >= 3:
                                inner_rings.append(in_coords)
                    return Polygon(outer_coords, inner_rings), "Polygon"

        # 4. MultiGeometry
        mg_elem = pm_elem.find(f".//{ns}MultiGeometry")
        if mg_elem is not None:
            # Check for polygons or linestrings inside MultiGeometry
            polys = []
            for p in mg_elem.findall(f".//{ns}Polygon"):
                o = p.find(f".//{ns}outerBoundaryIs//{ns}coordinates")
                if o is not None and o.text:
                    c = cls._parse_kml_coordinates(o.text)
                    if len(c) >= 3:
                        polys.append(Polygon(c))
            if polys:
                return MultiPolygon(polys), "MultiPolygon"

            lines = []
            for l in mg_elem.findall(f".//{ns}LineString"):
                c_elem = l.find(f"{ns}coordinates")
                if c_elem is not None and c_elem.text:
                    c = cls._parse_kml_coordinates(c_elem.text)
                    if len(c) >= 2:
                        lines.append(LineString(c))
            if lines:
                return MultiLineString(lines), "MultiLineString"

            points = []
            for pt in mg_elem.findall(f".//{ns}Point"):
                c_elem = pt.find(f"{ns}coordinates")
                if c_elem is not None and c_elem.text:
                    c = cls._parse_kml_coordinates(c_elem.text)
                    if c:
                        points.append(Point(c[0]))
            if points:
                return MultiPoint(points), "MultiPoint"

        return None, "Unknown"
