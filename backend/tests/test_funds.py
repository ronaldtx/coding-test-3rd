import pytest
from httpx import AsyncClient
from app.main import app
from app.db.session import get_db, SessionLocal

@pytest.fixture(scope="module")
def test_db():
    """Only use local database for testing"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.mark.asyncio
async def test_create_and_get_fund(test_db):
    """Testinging for create and get fund"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        payload = {
            "name": "Test Fund A",
            "gp_name": "Alpha Partners",
            "fund_type": "Venture",
            "vintage_year": 2023
        }
        response = await ac.post("/api/funds/", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Fund A"
        fund_id = data["id"]

        # Get fund
        response = await ac.get(f"/api/funds/{fund_id}")
        assert response.status_code == 200
        assert response.json()["name"] == "Test Fund A"

@pytest.mark.asyncio
async def test_list_funds():
    """Testing for get all funds"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/funds/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
