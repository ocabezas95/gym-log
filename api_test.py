import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from api import app

client = TestClient(app)

EXERCISES = [
    {"id": 1, "name": "Squat", "equipment": "Barbell"},
    {"id": 2, "name": "Bench Press", "equipment": "Barbell"},
]


def test_B1_save_valid_suggestion():
    """B1: PATCH with valid weight saves and returns the value."""
    with patch("api.load_exercises", return_value=list(EXERCISES)), \
         patch("api.load_suggestions", return_value={}), \
         patch("api.save_suggestions") as mock_save:
        resp = client.patch("/api/exercises/1/suggestion", json={"suggested_weight": 100.0})
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == 1
    assert data["suggested_weight"] == 100.0
    mock_save.assert_called_once()
    saved = mock_save.call_args[0][0]
    assert saved["1"] == 100.0


def test_B2_not_found_returns_404():
    """B2: PATCH for a non-existent exercise returns 404."""
    with patch("api.load_exercises", return_value=list(EXERCISES)), \
         patch("api.load_suggestions", return_value={}):
        resp = client.patch("/api/exercises/999/suggestion", json={"suggested_weight": 50.0})
    assert resp.status_code == 404


def test_B3_negative_weight_returns_422():
    """B3: PATCH with negative weight returns 422."""
    with patch("api.load_exercises", return_value=list(EXERCISES)):
        resp = client.patch("/api/exercises/1/suggestion", json={"suggested_weight": -5.0})
    assert resp.status_code == 422


def test_B4_missing_field_returns_422():
    """B4: PATCH with missing suggested_weight field returns 422."""
    with patch("api.load_exercises", return_value=list(EXERCISES)):
        resp = client.patch("/api/exercises/1/suggestion", json={})
    assert resp.status_code == 422


def test_B5_overwrite_existing_suggestion():
    """B5: PATCH overwrites an existing suggested_weight value."""
    with patch("api.load_exercises", return_value=list(EXERCISES)), \
         patch("api.load_suggestions", return_value={"1": 80.0}), \
         patch("api.save_suggestions") as mock_save:
        resp = client.patch("/api/exercises/1/suggestion", json={"suggested_weight": 90.0})
    assert resp.status_code == 200
    assert resp.json()["suggested_weight"] == 90.0
    saved = mock_save.call_args[0][0]
    assert saved["1"] == 90.0
