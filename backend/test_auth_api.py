import requests
import json

BASE_URL = "http://localhost:8000"

def test_registration():
    """Тест регистрации нового пользователя"""
    print("\n=== Тест регистрации ===")
    
    response = requests.post(
        f"{BASE_URL}/auth/register",
        json={
            "email": "test@example.com",
            "password": "testpassword123"
        }
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    return response.json()

def test_login(email, password):
    """Тест входа в систему"""
    print("\n=== Тест входа ===")
    
    response = requests.post(
        f"{BASE_URL}/auth/login",
        data={
            "username": email,
            "password": password
        }
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
    if response.status_code == 200:
        return response.json()["access_token"]
    return None

def test_chat(token):
    """Тест отправки сообщения в чат"""
    print("\n=== Тест чата ===")
    
    response = requests.post(
        f"{BASE_URL}/chat",
        json={
            "text": "Привет! Что вы умеете?"
        },
        headers={
            "Authorization": f"Bearer {token}"
        }
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

def test_profile(token):
    """Тест получения профиля"""
    print("\n=== Тест профиля ===")
    
    response = requests.get(
        f"{BASE_URL}/profile",
        headers={
            "Authorization": f"Bearer {token}"
        }
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

def test_health():
    """Тест проверки здоровья API"""
    print("\n=== Тест health check ===")
    
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

def test_chat_without_auth():
    """Тест чата без аутентификации (должен вернуть 401)"""
    print("\n=== Тест чата без аутентификации ===")
    
    response = requests.post(
        f"{BASE_URL}/chat",
        json={
            "text": "Этот запрос должен быть отклонен"
        }
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

def main():
    """Главная функция для запуска всех тестов"""
    print("=" * 50)
    print("Тестирование API с FastAPI-Users")
    print("=" * 50)
    
    # Тест health check
    test_health()
    
    # Тест чата без аутентификации
    test_chat_without_auth()
    
    # Тест регистрации
    user_data = test_registration()
    
    # Тест входа
    token = test_login("test@example.com", "testpassword123")
    
    if token:
        # Тест профиля
        test_profile(token)
        
        # Тест чата с аутентификацией
        test_chat(token)
    
    print("\n" + "=" * 50)
    print("Тестирование завершено!")
    print("=" * 50)

if __name__ == "__main__":
    main()

