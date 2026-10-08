from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class AreaMeasurement(BaseModel):
    sq_meters: float = Field(..., description="Area in square meters (m²)")
    hectares: float = Field(..., description="Area in hectares (ha)")
    sq_km: float = Field(..., description="Area in square kilometers (km²)")
    acres: float = Field(..., description="Area in acres")

class LengthMeasurement(BaseModel):
    meters: float = Field(..., description="Length in meters (m)")
    kilometers: float = Field(..., description="Length in kilometers (km)")
    miles: float = Field(..., description="Length in miles (mi)")

class PerimeterMeasurement(BaseModel):
    meters: float = Field(..., description="Perimeter in meters (m)")
    kilometers: float = Field(..., description="Perimeter in kilometers (km)")

class MeasurementValues(BaseModel):
    area: Optional[AreaMeasurement] = Field(None, description="Calculated area for polygon geometries")
    length: Optional[LengthMeasurement] = Field(None, description="Calculated length for linestring geometries")
    perimeter: Optional[PerimeterMeasurement] = Field(None, description="Calculated perimeter for polygon geometries")

class FeatureMeasurement(BaseModel):
    feature_id: str = Field(..., description="Feature index/ID from the source file")
    geometry_type: str = Field(..., description="Geometry type")
    is_measurable: bool = Field(..., description="Whether this geometry type supports spatial measurement")
    measurements: MeasurementValues = Field(default_factory=MeasurementValues, description="Calculated measurement data")
    projected_crs: Optional[str] = Field(None, description="Projected CRS used for metric calculation")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Feature attributes")
    status: str = Field("SUCCESS", description="Measurement status: SUCCESS, NO_MEASUREMENT_REQUIRED, SKIPPED")
    note: Optional[str] = Field(None, description="Additional context or notes about the measurement")

class MeasurementSummary(BaseModel):
    total_polygon_area_sq_meters: float = Field(0.0, description="Sum of all polygon areas in square meters")
    total_polygon_area_hectares: float = Field(0.0, description="Sum of all polygon areas in hectares")
    total_polygon_area_sq_km: float = Field(0.0, description="Sum of all polygon areas in square kilometers")
    total_linestring_length_meters: float = Field(0.0, description="Sum of all linestring lengths in meters")
    total_linestring_length_km: float = Field(0.0, description="Sum of all linestring lengths in kilometers")
    polygon_count: int = Field(0, description="Number of Polygon / MultiPolygon features")
    linestring_count: int = Field(0, description="Number of LineString / MultiLineString features")
    point_count: int = Field(0, description="Number of Point / MultiPoint features")
    unsupported_count: int = Field(0, description="Number of unsupported or skipped features")

class FileMeasurementsResponse(BaseModel):
    file_id: str = Field(..., description="Unique file identifier")
    filename: str = Field(..., description="Original filename")
    original_crs: str = Field(..., description="Original CRS of the uploaded file")
    default_projected_crs: str = Field(..., description="Optimal projected CRS selected for calculations")
    total_features: int = Field(..., description="Total feature count")
    summary: MeasurementSummary = Field(..., description="Aggregate measurement summary")
    features: List[FeatureMeasurement] = Field(..., description="Feature-by-feature measurement breakdown")
