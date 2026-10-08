import io
import pytest
from fastapi.testclient import TestClient

def test_health_endpoint(client: TestClient):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

def test_upload_shapefile_zip(client: TestClient, sample_zip_path):
    with open(sample_zip_path, "rb") as f:
        files = {"file": ("sample_parcels.zip", f, "application/zip")}
        response = client.post("/api/files/", files=files)
    
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["filename"] == "sample_parcels.zip"
    assert data["feature_count"] == 2
    assert data["status"] == "COMPLETED"
    assert "EPSG" in data["crs"]

    file_id = data["id"]

    # Test GET /api/files/{id}/
    info_resp = client.get(f"/api/files/{file_id}/")
    assert info_resp.status_code == 200
    info = info_resp.json()
    assert info["id"] == file_id
    assert info["feature_count"] == 2

    # Test GET /api/files/{id}/measurements/
    meas_resp = client.get(f"/api/files/{file_id}/measurements/")
    assert meas_resp.status_code == 200
    meas = meas_resp.json()
    assert meas["file_id"] == file_id
    assert meas["total_features"] == 2
    assert meas["summary"]["polygon_count"] == 2
    assert meas["summary"]["total_polygon_area_sq_meters"] > 0
    assert len(meas["features"]) == 2
    assert meas["features"][0]["measurements"]["area"]["sq_meters"] > 0

def test_upload_kml(client: TestClient, sample_kml_path):
    with open(sample_kml_path, "rb") as f:
        files = {"file": ("sample_infrastructure.kml", f, "application/vnd.google-earth.kml+xml")}
        response = client.post("/api/files/", files=files)

    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == "sample_infrastructure.kml"
    assert data["feature_count"] == 4
    assert data["status"] == "COMPLETED"

    file_id = data["id"]

    # Test measurements
    meas_resp = client.get(f"/api/files/{file_id}/measurements/")
    assert meas_resp.status_code == 200
    meas = meas_resp.json()
    assert meas["summary"]["polygon_count"] == 2
    assert meas["summary"]["linestring_count"] == 1
    assert meas["summary"]["point_count"] == 1
    assert meas["summary"]["total_polygon_area_sq_meters"] > 0
    assert meas["summary"]["total_linestring_length_meters"] > 0

def test_upload_invalid_extension(client: TestClient):
    file_bytes = io.BytesIO(b"fake text content")
    files = {"file": ("test.txt", file_bytes, "text/plain")}
    response = client.post("/api/files/", files=files)
    assert response.status_code == 400
    assert "Unsupported file format" in response.json()["detail"]

def test_get_nonexistent_file(client: TestClient):
    response = client.get("/api/files/nonexistent-id/")
    assert response.status_code == 404
