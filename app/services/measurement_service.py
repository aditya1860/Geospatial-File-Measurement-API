from typing import List, Tuple, Optional, Dict, Any
import pyproj
from shapely.geometry.base import BaseGeometry
from shapely.geometry import Polygon, MultiPolygon, LineString, MultiLineString, Point, MultiPoint

from app.services.crs_service import CRSService
from app.services.parser_service import ParsedFeature
from app.schemas.measurement import (
    FeatureMeasurement,
    MeasurementValues,
    AreaMeasurement,
    LengthMeasurement,
    PerimeterMeasurement,
    MeasurementSummary,
    FileMeasurementsResponse
)
from app.utils.logger import logger

class MeasurementService:
    @classmethod
    def calculate_feature_measurement(
        cls,
        feature: ParsedFeature,
        target_projected_crs: Optional[pyproj.CRS] = None
    ) -> FeatureMeasurement:
        """
        Calculates metric measurements for an individual feature by reprojecting to a metric projected CRS.
        """
        geom = feature.geometry
        geom_type = feature.geometry_type

        # Case 1: Null or empty geometry
        if geom is None or geom.is_empty:
            return FeatureMeasurement(
                feature_id=feature.feature_id,
                geometry_type=geom_type or "Empty",
                is_measurable=False,
                measurements=MeasurementValues(),
                projected_crs=None,
                properties=feature.properties,
                status="SKIPPED",
                note="Geometry is empty or null."
            )

        # Case 2: Point / MultiPoint (No measurement required per specification)
        if geom_type in ["Point", "MultiPoint"]:
            return FeatureMeasurement(
                feature_id=feature.feature_id,
                geometry_type=geom_type,
                is_measurable=False,
                measurements=MeasurementValues(),
                projected_crs=str(feature.crs),
                properties=feature.properties,
                status="NO_MEASUREMENT_REQUIRED",
                note="Point geometries do not have area or length measurements."
            )

        # Reproject geometry into projected CRS
        try:
            projected_geom, chosen_crs = CRSService.transform_geometry_to_projected(
                geom,
                feature.crs,
                target_projected_crs
            )
            crs_name = chosen_crs.to_string() if hasattr(chosen_crs, "to_string") else str(chosen_crs)
        except Exception as e:
            logger.error(f"Projection failed for feature {feature.feature_id}: {e}")
            return FeatureMeasurement(
                feature_id=feature.feature_id,
                geometry_type=geom_type,
                is_measurable=False,
                measurements=MeasurementValues(),
                projected_crs=None,
                properties=feature.properties,
                status="SKIPPED",
                note=f"Coordinate transformation failed: {str(e)}"
            )

        # Case 3: Polygon / MultiPolygon
        if geom_type in ["Polygon", "MultiPolygon"]:
            area_m2 = float(projected_geom.area)
            perimeter_m = float(projected_geom.length)

            area_ha = area_m2 / 10_000.0
            area_km2 = area_m2 / 1_000_000.0
            area_acres = area_m2 * 0.000247105

            perimeter_km = perimeter_m / 1000.0

            return FeatureMeasurement(
                feature_id=feature.feature_id,
                geometry_type=geom_type,
                is_measurable=True,
                measurements=MeasurementValues(
                    area=AreaMeasurement(
                        sq_meters=round(area_m2, 4),
                        hectares=round(area_ha, 6),
                        sq_km=round(area_km2, 6),
                        acres=round(area_acres, 4)
                    ),
                    perimeter=PerimeterMeasurement(
                        meters=round(perimeter_m, 4),
                        kilometers=round(perimeter_km, 6)
                    )
                ),
                projected_crs=crs_name,
                properties=feature.properties,
                status="SUCCESS"
            )

        # Case 4: LineString / MultiLineString
        if geom_type in ["LineString", "MultiLineString"]:
            length_m = float(projected_geom.length)
            length_km = length_m / 1000.0
            length_mi = length_m * 0.000621371

            return FeatureMeasurement(
                feature_id=feature.feature_id,
                geometry_type=geom_type,
                is_measurable=True,
                measurements=MeasurementValues(
                    length=LengthMeasurement(
                        meters=round(length_m, 4),
                        kilometers=round(length_km, 6),
                        miles=round(length_mi, 6)
                    )
                ),
                projected_crs=crs_name,
                properties=feature.properties,
                status="SUCCESS"
            )

        # Case 5: Unsupported Geometry Type
        return FeatureMeasurement(
            feature_id=feature.feature_id,
            geometry_type=geom_type,
            is_measurable=False,
            measurements=MeasurementValues(),
            projected_crs=None,
            properties=feature.properties,
            status="SKIPPED",
            note=f"Unsupported geometry type '{geom_type}' for measurement."
        )

    @classmethod
    def process_all_measurements(
        cls,
        features: List[ParsedFeature],
        source_crs: pyproj.CRS
    ) -> Tuple[List[FeatureMeasurement], MeasurementSummary, str]:
        """
        Processes measurements for all parsed features and computes summary statistics.
        """
        # Determine global projected CRS if multiple features exist
        default_projected_crs_name = "EPSG:4326"
        if features:
            valid_geoms = [f.geometry for f in features if f.geometry is not None and not f.geometry.is_empty]
            if valid_geoms:
                # Use first valid geometry to establish default projected CRS
                opt_crs = CRSService.get_optimal_projected_crs(valid_geoms[0], source_crs)
                default_projected_crs_name = opt_crs.to_string()

        feature_measurements: List[FeatureMeasurement] = []
        
        tot_area_m2 = 0.0
        tot_length_m = 0.0
        poly_count = 0
        line_count = 0
        point_count = 0
        unsupported_count = 0

        for f in features:
            meas = cls.calculate_feature_measurement(f)
            feature_measurements.append(meas)

            if meas.geometry_type in ["Polygon", "MultiPolygon"]:
                poly_count += 1
                if meas.measurements.area:
                    tot_area_m2 += meas.measurements.area.sq_meters
            elif meas.geometry_type in ["LineString", "MultiLineString"]:
                line_count += 1
                if meas.measurements.length:
                    tot_length_m += meas.measurements.length.meters
            elif meas.geometry_type in ["Point", "MultiPoint"]:
                point_count += 1
            else:
                unsupported_count += 1

        summary = MeasurementSummary(
            total_polygon_area_sq_meters=round(tot_area_m2, 4),
            total_polygon_area_hectares=round(tot_area_m2 / 10_000.0, 6),
            total_polygon_area_sq_km=round(tot_area_m2 / 1_000_000.0, 6),
            total_linestring_length_meters=round(tot_length_m, 4),
            total_linestring_length_km=round(tot_length_m / 1000.0, 6),
            polygon_count=poly_count,
            linestring_count=line_count,
            point_count=point_count,
            unsupported_count=unsupported_count
        )

        return feature_measurements, summary, default_projected_crs_name
