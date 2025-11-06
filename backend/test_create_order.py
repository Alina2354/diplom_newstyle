import asyncio
import aiohttp
import json

async def test_create_order():
    """Создает тестовый заказ через API"""
    # Здесь нужно указать реальный JWT токен
    # Для теста можно получить его через логин
    token = input("Введите JWT токен (или оставьте пустым для теста без токена): ").strip()
    
    url = "http://localhost:8000/orders"
    
    headers = {
        "Content-Type": "application/json"
    }
    
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    data = {
        "title": "Тестовый заказ: Ремонт одежды - хлопок - тест",
        "status": "новая"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data) as response:
            print(f"Status: {response.status}")
            text = await response.text()
            print(f"Response: {text}")

if __name__ == "__main__":
    asyncio.run(test_create_order())



