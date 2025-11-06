import asyncio
import aiohttp

async def test_cors():
    async with aiohttp.ClientSession() as session:
        try:
            # Проверяем основной endpoint
            async with session.get('http://localhost:8000/') as response:
                print(f"GET /: Status {response.status}")
                print(f"Headers: {dict(response.headers)}")
                
            # Проверяем health endpoint
            async with session.get('http://localhost:8000/health') as response:
                print(f"\nGET /health: Status {response.status}")
                print(f"Headers: {dict(response.headers)}")
                
            # Проверяем OPTIONS запрос
            async with session.options('http://localhost:8000/auth/register') as response:
                print(f"\nOPTIONS /auth/register: Status {response.status}")
                print(f"Access-Control-Allow-Origin: {response.headers.get('Access-Control-Allow-Origin', 'NOT FOUND')}")
                print(f"Access-Control-Allow-Methods: {response.headers.get('Access-Control-Allow-Methods', 'NOT FOUND')}")
                print(f"Access-Control-Allow-Headers: {response.headers.get('Access-Control-Allow-Headers', 'NOT FOUND')}")
                
        except aiohttp.ClientError as e:
            print(f"Ошибка подключения: {e}")
            print("Убедитесь что backend запущен на порту 8000")

if __name__ == "__main__":
    print("Проверка CORS настроек...\n")
    asyncio.run(test_cors())
















