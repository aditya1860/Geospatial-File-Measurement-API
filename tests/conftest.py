import os
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Ensure app directory is on path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.main import app
from app.config import settings

@pytest.fixture(scope="session")
def client():
    # Use TestClient
    with TestClient(app) as test_client:
        yield test_client

@pytest.fixture
def samples_dir():
    return project_root / "samples"

@pytest.fixture
def sample_zip_path(samples_dir):
    return samples_dir / "sample_parcels.zip"

@pytest.fixture
def sample_kml_path(samples_dir):
    return samples_dir / "sample_infrastructure.kml"
