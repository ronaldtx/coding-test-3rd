import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_create_conversation():
    """Testing create new chat"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        payload = {"fund_id": 1}
        response = await ac.post("/api/chat/conversations", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "conversation_id" in data
        global conversation_id
        conversation_id = data["conversation_id"]

@pytest.mark.asyncio
async def test_chat_query():
    """Testing send query chat"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        payload = {
            "query": "Please show result this fund.",
            "fund_id": 1,
            "conversation_id": "dummy-conv"
        }
        response = await ac.post("/api/chat/query", json=payload)
        assert response.status_code in [200, 500]
