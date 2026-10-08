from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class GeometrySchema(BaseModel):
    type: str = Field(..., description="GeoJSON geometry type (Point, Polygon, LineString, MultiPolygon, etc.)")
    coordinates: Any = Field(..., description="Geometry coordinate array")

class FeatureDetail(BaseModel):
    feature_id: str = Field(..., description="Unique identifier or index of the feature")
    geometry_type: str = Field(..., description="Type of geometry")
    geometry: GeometrySchema = Field(..., description="GeoJSON formatted geometry representation")
    crs: str = Field(..., description="Native CRS of the feature")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Feature attributes and metadata properties")
