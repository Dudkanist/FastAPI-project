from fastapi.testclient import TestClient
from app.main import app
import pytest

client = TestClient(app)

def test_read_main():
    """Проверка доступности API (Healthcheck)"""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "alive", "database": "connected"}

def test_register_user():
    """Тест регистрации нового пользователя"""
    response = client.post(
        "/register",
        json={"email": "tester@example.com", "password": "testpassword"}
    )
    assert response.status_code == 200
    assert response.json()["email"] == "tester@example.com"
    assert "id" in response.json()

def test_bio_logic():
    """Тест нашего 'биоинформатического движка' через API"""
    # 1. Получаем токен (сначала регистрируем, если нужно, или используем имеющегося)
    login_response = client.post(
        "/token",
        data={"username": "tester@example.com", "password": "testpassword"}
    )
    token = login_response.json()["access_token"]
    
    # 2. Отправляем сиквенс на анализ
    seq_data = {
        "name": "Test DNA",
        "raw_sequence": "ATGC ATGC",
        "molecule_type": "DNA"
    }
    response = client.post(
        "/sequences/",
        json=seq_data,
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    # Проверяем математику: для ATGCATGC GC-состав должен быть 50.0%
    assert data["analysis"]["gc_content"] == 50.0
    # Проверяем очистку: пробел в 'ATGC ATGC' должен исчезнуть
    assert data["raw_sequence"] == "ATGCATGC"
