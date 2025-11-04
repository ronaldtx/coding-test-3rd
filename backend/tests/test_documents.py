import pytest
from httpx import AsyncClient
from app.main import app
from io import BytesIO

@pytest.mark.asyncio
async def test_upload_invalid_file():
    """Testing for Upload not PDF File"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        file = {'file': ('test.txt', BytesIO(b"fake data"), 'text/plain')}
        response = await ac.post("/api/documents/upload", files=file)
        assert response.status_code == 400
        assert "Only PDF files" in response.text

@pytest.mark.asyncio
async def test_list_documents():
    """Testing for get all documents"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/documents/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
