import asyncio
import aiohttp
import json

async def test_register():
    async with aiohttp.ClientSession() as session:
        # Данные для регистрации
        data = {
            "email": "test@example.com",
            "password": "testpass123"
        }
        
        try:
            async with session.post('http://localhost:8000/auth/register', json=data) as response:
                print(f"Status: {response.status}")
                print(f"Headers: {dict(response.headers)}")
                
                text = await response.text()
                print(f"\nResponse body: {text}")
                
                if response.status == 200:
                    print("\n✅ Регистрация успешна!")
                else:
                    print(f"\n❌ Ошибка: {response.status}")
                    
        except aiohttp.ClientError as e:
            print(f"Ошибка подключения: {e}")

if __name__ == "__main__":
    print("Тестирование регистрации...\n")
    asyncio.run(test_register())
















