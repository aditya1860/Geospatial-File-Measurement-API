import math
from typing import Optional, Tuple
import pyproj
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform
from app.utils.logger import logger

class CRSService:
    @staticmethod
    def parse_crs_from_prj_text(prj_text: str) -> pyproj.CRS:
        """
        Parses a WKT or PRJ string to a pyproj.CRS object.
        Defaults to EPSG:4326 if parsing fails.
        """
        try:
            return pyproj.CRS.from_user_input(prj_text)
        except Exception as e:
            logger.warning(f"Failed to parse CRS from PRJ text: {e}. Falling back to EPSG:4326.")
            return pyproj.CRS.from_epsg(4326)

    @staticmethod
    def get_utm_epsg_for_latlon(lat: float, lon: float) -> int:
        """
        Calculates the appropriate WGS 84 UTM EPSG code for given (lat, lon).
        Formula:
        Zone = floor((lon + 180) / 6) + 1
        EPSG = 32600 + Zone (North) or 32700 + Zone (South)
        """
        # Clamp latitude and wrap longitude
        lon = ((lon + 180) % 360) - 180
        lat = max(min(lat, 89.9), -89.9)

        # High latitude polar regions (UPS)
        if lat > 84.0:
            return 32661  # WGS 84 / UPS North (N)
        if lat < -80.0:
            return 32761  # WGS 84 / UPS South (S)

        utm_zone = int(math.floor((lon + 180) / 6.0)) + 1
        if lat >= 0:
            return 32600 + utm_zone
        else:
            return 32700 + utm_zone

    @classmethod
    def get_optimal_projected_crs(cls, geometry: BaseGeometry, source_crs: pyproj.CRS) -> pyproj.CRS:
        """
        Determines the optimal projected coordinate system for a given geometry.
        If source CRS is already projected in metric units, preserves it.
        If geographic (e.g. EPSG:4326), computes the local UTM projection based on centroid.
        """
        try:
            if source_crs.is_projected:
                # Check if units are meters or feet
                return source_crs

            # For geographic coordinates, find centroid in lat/lon
            centroid = geometry.centroid
            lon, lat = centroid.x, centroid.y
            
            # If coordinates look inverted (e.g. lat > 90), clamp safely
            if abs(lon) > 180 and abs(lat) <= 90:
                lon, lat = lat, lon

            utm_epsg = cls.get_utm_epsg_for_latlon(lat, lon)
            return pyproj.CRS.from_epsg(utm_epsg)
        except Exception as e:
            logger.warning(f"Error determining UTM CRS: {e}. Falling back to EPSG:3857.")
            return pyproj.CRS.from_epsg(3857)

    @classmethod
    def transform_geometry_to_projected(
        cls, 
        geometry: BaseGeometry, 
        source_crs: pyproj.CRS, 
        target_crs: Optional[pyproj.CRS] = None
    ) -> Tuple[BaseGeometry, pyproj.CRS]:
        """
        Transforms a shapely geometry from source_crs to target_crs (or auto-selected projected CRS).
        Uses always_xy=True for robust lon/lat -> easting/northing order.
        """
        if target_crs is None:
            target_crs = cls.get_optimal_projected_crs(geometry, source_crs)

        if source_crs.equals(target_crs):
            return geometry, target_crs

        transformer = pyproj.Transformer.from_crs(
            source_crs, 
            target_crs, 
            always_xy=True
        )
        
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            projected_geom = transform(transformer.transform, geometry)

        return projected_geom, target_crs

    @staticmethod
    def get_geod() -> pyproj.Geod:
        """Returns standard WGS84 Geod instance for geodesic calculations."""
        return pyproj.Geod(ellps="WGS84")
