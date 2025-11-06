# Документация работы приложения "Ателье Новый Стиль"

## Содержание
1. [Общая архитектура приложения](#общая-архитектура-приложения)
2. [Связь между бэкендом и фронтендом](#связь-между-бэкендом-и-фронтендом)
3. [CRUD операции](#crud-операции)
4. [API и эндпоинты](#api-и-эндпоинты)
5. [Основные функции бэкенда](#основные-функции-бэкенда)
6. [Основные функции фронтенда](#основные-функции-фронтенда)
7. [База данных и модели](#база-данных-и-модели)
8. [Аутентификация и авторизация](#аутентификация-и-авторизация)

---

## Общая архитектура приложения

### Структура проекта
```
web_app1/
├── backend/          # FastAPI бэкенд
│   ├── main.py       # Главный файл приложения с API эндпоинтами
│   ├── models.py     # SQLAlchemy модели данных
│   ├── schemas.py    # Pydantic схемы для валидации
│   ├── database.py   # Настройка подключения к БД
│   ├── auth.py       # Настройка аутентификации
│   └── knowledge_base.py  # База знаний для чат-бота
├── frontend/         # HTML/JavaScript фронтенд
│   ├── templates/    # HTML страницы
│   └── static/       # CSS стили
└── uploads/          # Загруженные файлы (изображения)
```

### Технологический стек

**Бэкенд:**
- **FastAPI** - современный веб-фреймворк для создания API
- **SQLAlchemy** - ORM для работы с базой данных
- **SQLite** - база данных (асинхронная через aiosqlite)
- **FastAPI Users** - библиотека для аутентификации
- **JWT** - токены для авторизации
- **Google Gemini AI** - интеграция с AI для чат-бота
- **Pydantic** - валидация данных

**Фронтенд:**
- **Vanilla JavaScript** - без фреймворков
- **HTML5/CSS3** - разметка и стилизация
- **Fetch API** - для HTTP запросов к бэкенду

---

@app.post("/auth/register-simple", status_code=http_status.HTTP_201_CREATED)
async def simple_register(req: RegisterRequest):
    """
    Простой endpoint для регистрации
    
    Упрощенная версия регистрации без использования FastAPI Users.
    Создает пользователя напрямую в БД.
    
    Используется для совместимости или специальных случаев.
    """
    try:
        logger.info(f"Попытка регистрации: {req.email}")
        async for session in get_async_session():
            result = await session.execute(
                select(User).where(User.email == req.email)
            )
            existing_user = result.scalar_one_or_none()
            if existing_user:
                raise HTTPException(
                    status_code=http_status.HTTP_409_CONFLICT, 
                    detail="Этот email уже зарегистрирован"
                )
            hashed_password = pwd_helper.hash(req.password)
            
            
            new_user = User(
                email=req.email,
                hashed_password=hashed_password,  
                is_active=True,     
                is_superuser=False, 
                is_verified=False   
            )
            
            
            session.add(new_user)
            
            
            await session.commit()
            
            
            await session.refresh(new_user)
            
            logger.info(f"Пользователь создан: {req.email}")
            return {
                "message": "User created successfully", 
                "user_id": new_user.id, 
                "email": new_user.email
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка регистрации: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=str(e)
        )

app.include_router(
    fastapi_users.get_users_router(UserRead, UserCreate),
    prefix="/users",
    tags=["users"],
)

## Связь между бэкендом и фронтендом

### Механизм взаимодействия

Приложение использует архитектуру **REST API**, где фронтенд и бэкенд взаимодействуют через HTTP запросы.

#### 1. **API URL конфигурация**

В файле `frontend/templates/auth.js` определяется базовый URL для API:
```javascript
var API_URL = typeof window !== 'undefined' && window.location.port === '8080' 
    ? '/api'  // Используем прокси если фронтенд на порту 8080
    : 'http://localhost:8000/api';  // Прямой URL к бэкенду
```

#### 2. **CORS настройки**

Бэкенд настроен для принятия запросов с любого домена (для разработки):
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

#### 3. **Схема взаимодействия**

```
┌─────────────┐                    ┌─────────────┐
│  Фронтенд   │  HTTP Request      │   Бэкенд    │
│  (Browser)  │ ──────────────────> │  (FastAPI)  │
│             │                    │             │
│  JavaScript │  JSON Response     │   Python    │
│  (fetch)    │ <────────────────── │  (FastAPI)  │
└─────────────┘                    └─────────────┘
         │                                 │
         │                                 │
         └─────────> JWT Token <──────────┘
         (localStorage)              (Генерация)
```

#### 4. **Пример запроса**

**Фронтенд (JavaScript):**
```javascript
const response = await fetch(`${API_URL}/orders`, {
    method: 'POST',
    headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
    },
    body: JSON.stringify(requestBody)
});
const data = await response.json();
```

**Бэкенд (Python/FastAPI):**
```python
@app.post("/orders", response_model=OrderOut)
async def create_order(
    order: OrderCreate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    # Обработка запроса
    db_order = Order(...)
    session.add(db_order)
    await session.commit()
    return db_order
```

#### 5. **Управление состоянием**

Фронтенд использует **localStorage** для хранения JWT токена:
```javascript
// Сохранение токена после логина
AuthManager.setToken(token);

// Использование токена в запросах
const token = AuthManager.getToken();
headers: { 'Authorization': `Bearer ${token}` }
```

---

## CRUD операции

Приложение поддерживает полный набор CRUD операций для различных сущностей.

### 1. **Заказы (Orders)**

#### CREATE (Создание)
- **Эндпоинт:** `POST /api/orders`
- **Требует авторизации:** Да
- **Описание:** Создание нового заказа пользователем
- **Фронтенд:** `order-forms.js` → `submitOrder()`
- **Бэкенд:** `main.py` → `create_order()`

**Процесс:**
1. Пользователь заполняет форму заказа на фронтенде
2. JavaScript собирает данные и отправляет POST запрос
3. Бэкенд валидирует данные через Pydantic схему `OrderCreate`
4. Создается запись в таблице `orders` с привязкой к `user_id`
5. Возвращается созданный заказ с ID

#### READ (Чтение)
- **Эндпоинт:** `GET /api/orders/me` - заказы текущего пользователя
- **Эндпоинт:** `GET /api/orders/all` - все заказы (только для админов)
- **Требует авторизации:** Да
- **Фронтенд:** `dashboard.js` → `loadUserOrders()`
- **Бэкенд:** `main.py` → `get_my_orders()`, `get_all_orders_admin()`

**Процесс:**
1. Фронтенд отправляет GET запрос с JWT токеном
2. Бэкенд проверяет токен и извлекает `user_id`
3. Выполняется SQL запрос: `SELECT * FROM orders WHERE user_id = ?`
4. Данные возвращаются в формате JSON
5. Фронтенд отображает заказы в таблице

#### UPDATE (Обновление)
- **Эндпоинт:** `PATCH /api/orders/{order_id}/status`
- **Требует авторизации:** Да (только админ)
- **Описание:** Изменение статуса заказа
- **Бэкенд:** `main.py` → `update_order_status()`

**Процесс:**
1. Администратор выбирает заказ и новый статус
2. Отправляется PATCH запрос с `order_id` и новым статусом
3. Бэкенд проверяет права администратора
4. Обновляется запись в БД
5. Возвращается обновленный заказ

#### DELETE (Удаление)
- Для заказов удаление не реализовано (только изменение статуса)

---

### 2. **Костюмы (Costumes)**

#### CREATE (Создание)
- **Эндпоинт:** `POST /api/costumes`
- **Требует авторизации:** Да (только админ)
- **Фронтенд:** `costumes.js` → форма администратора
- **Бэкенд:** `main.py` → `create_costume()`

**Особенности:**
- Загрузка изображения через `multipart/form-data`
- Генерация уникального имени файла через UUID
- Сохранение файла в директорию `uploads/`

#### READ (Чтение)
- **Эндпоинт:** `GET /api/costumes` - список всех костюмов
- **Эндпоинт:** `GET /api/costumes/{costume_id}` - один костюм
- **Требует авторизации:** Нет (публичный доступ)
- **Фронтенд:** `costumes.js` → `loadCostumes()`
- **Бэкенд:** `main.py` → `list_costumes()`, `get_costume()`

#### UPDATE (Обновление)
- **Эндпоинт:** `PUT /api/costumes/{costume_id}`
- **Требует авторизации:** Да (только админ)
- **Бэкенд:** `main.py` → `update_costume()`

**Особенности:**
- При обновлении изображения старое удаляется
- Можно обновить только отдельные поля

#### DELETE (Удаление)
- **Эндпоинт:** `DELETE /api/costumes/{costume_id}`
- **Требует авторизации:** Да (только админ)
- **Фронтенд:** `costumes.js` → кнопка "Удалить"
- **Бэкенд:** `main.py` → `delete_costume()`

---

### 3. **Профили пользователей (Profiles)**

#### CREATE (Создание)
- Автоматически создается при первом обновлении профиля
- **Эндпоинт:** `PUT /api/profile` (создает если не существует)

#### READ (Чтение)
- **Эндпоинт:** `GET /api/profile`
- **Требует авторизации:** Да
- **Фронтенд:** `dashboard.js` → `loadUserProfile()`
- **Бэкенд:** `main.py` → `get_profile()`

#### UPDATE (Обновление)
- **Эндпоинт:** `PUT /api/profile` - обновление данных
- **Эндпоинт:** `POST /api/profile/photo` - загрузка фото
- **Фронтенд:** `dashboard.js` → `setupProfileForm()`
- **Бэкенд:** `main.py` → `update_profile()`, `upload_profile_photo()`

**Процесс обновления профиля:**
1. Пользователь заполняет форму (имя, телефон, возраст)
2. JavaScript собирает данные и отправляет PUT запрос
3. Бэкенд проверяет валидность (например, возраст 0-120)
4. Если профиль не существует - создается новый
5. Обновляются поля в таблице `profiles`
6. Возвращается успешный ответ

---

### 4. **Бронирования (Reservations)**

#### CREATE (Создание)
- **Эндпоинт:** `POST /api/reservations`
- **Требует авторизации:** Да
- **Фронтенд:** `costumes.js` → модальное окно бронирования
- **Бэкенд:** `main.py` → `create_reservation()`

**Особенности:**
- Проверка конфликтов дат перед созданием
- Валидация: `date_to` не может быть раньше `date_from`

#### READ (Чтение)
- **Эндпоинт:** `GET /api/reservations/me` - бронирования пользователя
- **Эндпоинт:** `GET /api/reservations/all` - все бронирования (админ)
- **Эндпоинт:** `GET /api/costumes/{id}/availability` - проверка доступности
- **Бэкенд:** `main.py` → `my_reservations()`, `all_reservations_admin()`, `costume_availability()`

#### DELETE (Удаление)
- **Эндпоинт:** `DELETE /api/reservations/{reservation_id}`
- **Требует авторизации:** Да (только админ)
- **Бэкенд:** `main.py` → `delete_reservation_admin()`

---

## API и эндпоинты

### Группировка эндпоинтов

#### 1. **Аутентификация (`/auth`)**

| Метод | Эндпоинт | Описание | Авторизация |
|-------|----------|----------|-------------|
| POST | `/auth/register` | Регистрация нового пользователя | Нет |
| POST | `/auth/register-simple` | Упрощенная регистрация | Нет |
| POST | `/auth/login` | Вход в систему | Нет |
| POST | `/auth/logout` | Выход из системы | Да |
| POST | `/auth/verify` | Верификация email | Нет |

**Пример использования:**
```javascript
// Регистрация
const response = await fetch(`${API_URL}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        email: 'user@example.com',
        password: 'password123'
    })
});

// Логин
const loginResponse = await fetch(`${API_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
        username: 'user@example.com',
        password: 'password123'
    })
});
const { access_token } = await loginResponse.json();
AuthManager.setToken(access_token);
```

---

#### 2. **Чат-бот (`/chat`)**

| Метод | Эндпоинт | Описание | Авторизация |
|-------|----------|----------|-------------|
| POST | `/chat` | Публичный чат (без авторизации) | Нет |
| POST | `/chat/authenticated` | Чат для авторизованных | Да |

**Процесс работы:**
1. Пользователь отправляет вопрос
2. Бэкенд сначала проверяет базу знаний (`knowledge_base.py`)
3. Если ответ найден - возвращается сразу
4. Если нет - используется Google Gemini AI
5. Если AI недоступен - возвращается fallback ответ

**Пример:**
```javascript
const response = await fetch(`${API_URL}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text: 'Где находится ателье?' })
});
const { response: answer } = await response.json();
```

---

#### 3. **Заказы (`/orders`)**

| Метод | Эндпоинт | Описание | Авторизация |
|-------|----------|----------|-------------|
| POST | `/orders` | Создание заказа | Да |
| GET | `/orders/me` | Мои заказы | Да |
| GET | `/orders/all` | Все заказы | Да (админ) |
| PATCH | `/orders/{id}/status` | Изменение статуса | Да (админ) |

**Статусы заказов:**
- `новая` - только что созданный заказ
- `в обработке` - заказ в работе
- `завершена` - заказ выполнен

---

#### 4. **Профиль (`/profile`)**

| Метод | Эндпоинт | Описание | Авторизация |
|-------|----------|----------|-------------|
| GET | `/profile` | Получить профиль | Да |
| PUT | `/profile` | Обновить профиль | Да |
| POST | `/profile/photo` | Загрузить фото | Да |

**Формат данных профиля:**
```json
{
    "id": 1,
    "email": "user@example.com",
    "name": "Иван Иванов",
    "phone": "+79001234567",
    "age": 30,
    "photo_url": "/uploads/user_1_photo.jpg",
    "is_active": true,
    "is_verified": false,
    "is_superuser": false
}
```

---

#### 5. **Костюмы (`/costumes`)**

| Метод | Эндпоинт | Описание | Авторизация |
|-------|----------|----------|-------------|
| GET | `/costumes` | Список костюмов | Нет |
| GET | `/costumes/{id}` | Один костюм | Нет |
| POST | `/costumes` | Создать костюм | Да (админ) |
| PUT | `/costumes/{id}` | Обновить костюм | Да (админ) |
| DELETE | `/costumes/{id}` | Удалить костюм | Да (админ) |
| GET | `/costumes/{id}/availability` | Проверка доступности | Нет |

---

#### 6. **Бронирования (`/reservations`)**

| Метод | Эндпоинт | Описание | Авторизация |
|-------|----------|----------|-------------|
| POST | `/reservations` | Создать бронирование | Да |
| GET | `/reservations/me` | Мои бронирования | Да |
| GET | `/reservations/all` | Все бронирования | Да (админ) |
| DELETE | `/reservations/{id}` | Удалить бронирование | Да (админ) |

---

## Основные функции бэкенда

### 1. **Инициализация приложения (`main.py`)**

#### `lifespan()` - функция жизненного цикла
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Выполняется при запуске приложения
    await create_tables()  # Создание таблиц БД
    # Создание/обновление суперпользователя
    yield
    # Код при остановке (если нужен)
```

**Что делает:**
- Создает все таблицы в БД при первом запуске
- Проверяет наличие суперпользователя
- Создает суперпользователя если его нет
- Инициализирует Gemini AI (если есть API ключ)

---

### 2. **Работа с базой знаний (`main.py`)**

#### `preprocess_text(text: str) -> str`
**Назначение:** Предобработка текста перед поиском
**Процесс:**
1. Приведение к нижнему регистру
2. Удаление знаков препинания
3. Замена множественных пробелов на один

#### `find_in_knowledge_base(user_input: str) -> str`
**Назначение:** Поиск ответа в базе знаний
**Процесс:**
1. Проверка на приветствия
2. Проверка общих вопросов
3. Поиск точных совпадений терминов
4. Поиск по ключевым словам в вопросах
5. Возврат лучшего совпадения или `None`

**Пример:**
```python
# Пользователь: "Где находится ателье?"
# Результат: "Ателье 'Новый Стиль' находится по адресу: улица Гагарина, дом 36/1."
```

---

### 3. **Аутентификация (`auth.py`)**

#### `get_jwt_strategy() -> JWTStrategy`
**Назначение:** Настройка JWT стратегии
- Секретный ключ из переменной окружения
- Время жизни токена: 3600 секунд (1 час)

#### `current_active_user`
**Назначение:** Dependency для проверки авторизованного пользователя
**Использование:**
```python
@app.get("/profile")
async def get_profile(user: User = Depends(current_active_user)):
    # user - авторизованный пользователь
    # Если токен невалиден - автоматически вернется 401
```

#### `require_admin(user: User)`
**Назначение:** Проверка прав администратора
**Использование:**
```python
@app.delete("/costumes/{id}")
async def delete_costume(user: User = Depends(require_admin)):
    # Только для администраторов
    # Если не админ - вернется 403 Forbidden
```

---

### 4. **Работа с базой данных (`database.py`)**

#### `get_async_session() -> AsyncSession`
**Назначение:** Получение сессии базы данных
**Использование:**
```python
async def create_order(..., session: AsyncSession = Depends(get_async_session)):
    # Использование сессии для работы с БД
    db_order = Order(...)
    session.add(db_order)
    await session.commit()
```

#### `create_tables()`
**Назначение:** Создание всех таблиц в БД
**Процесс:**
1. Читает метаданные из моделей SQLAlchemy
2. Создает таблицы если их нет
3. Выполняет миграции (например, добавление колонки `costume_id`)

---

### 5. **Валидация данных (`schemas.py`)**

#### Pydantic модели
**Назначение:** Валидация и сериализация данных
**Примеры:**
- `UserCreate` - данные для регистрации
- `UserRead` - данные пользователя для ответа
- `OrderCreate` - данные для создания заказа
- `ProfileUpdate` - данные для обновления профиля

**Преимущества:**
- Автоматическая валидация типов
- Преобразование данных в JSON
- Обработка ошибок валидации

---

### 6. **Работа с файлами (`main.py`)**

#### Загрузка изображений
**Процесс:**
1. Проверка расширения файла (только .jpg, .jpeg, .png)
2. Генерация уникального имени через UUID
3. Сохранение в директорию `uploads/`
4. Сохранение имени файла в БД
5. Возврат URL для доступа к файлу

**Пример:**
```python
@app.post("/profile/photo")
async def upload_profile_photo(
    image: UploadFile = File(...),
    user: User = Depends(current_active_user)
):
    # Сохранение файла
    safe_name = f"user_{user.id}_{image.filename}"
    out_path = UPLOAD_DIR / safe_name
    with open(out_path, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)
    # Сохранение в БД
    prof.photo_filename = safe_name
    await session.commit()
```

---

## Основные функции фронтенда

### 1. **Управление авторизацией (`auth.js`)**

#### `AuthManager` класс
**Методы:**
- `getToken()` - получить JWT токен из localStorage
- `setToken(token)` - сохранить токен
- `removeToken()` - удалить токен (при выходе)
- `isAuthenticated()` - проверить наличие токена
- `getAuthHeader()` - получить заголовок Authorization
- `requireAuth()` - редирект на логин если не авторизован
- `redirectIfAuthenticated()` - редирект если уже авторизован

**Использование:**
```javascript
// Проверка перед доступом к странице
if (!AuthManager.requireAuth()) {
    return; // Редирект на логин
}

// Добавление токена в запрос
const token = AuthManager.getToken();
fetch(url, {
    headers: {
        'Authorization': `Bearer ${token}`
    }
});
```

---

### 2. **Работа с профилем (`dashboard.js`)**

#### `loadUserProfile()`
**Назначение:** Загрузка данных профиля пользователя
**Процесс:**
1. Отправляет GET запрос к `/api/profile`
2. Обрабатывает ответ
3. Заполняет форму данными
4. Отображает информацию на странице
5. Загружает фото профиля

#### `setupProfileForm()`
**Назначение:** Настройка формы профиля
**Функции:**
- Обработка отправки формы (имя, телефон, возраст)
- Загрузка фото профиля
- Показ/скрытие формы
- Валидация данных

**Пример:**
```javascript
form.addEventListener('submit', async function(e) {
    e.preventDefault();
    const body = {
        name: nameInput.value.trim(),
        phone: phoneInput.value.trim(),
        age: parseInt(ageInput.value) || null
    };
    const response = await fetch(`${API_URL}/profile`, {
        method: 'PUT',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(body)
    });
});
```

---

### 3. **Работа с заказами (`order-forms.js`)**

#### `submitOrder(formData, orderType)`
**Назначение:** Отправка заказа на сервер
**Процесс:**
1. Проверка наличия токена
2. Формирование заголовка заказа
3. Отправка POST запроса к `/api/orders`
4. Обработка ответа
5. Обновление списка заказов

#### `handleOrderFormSubmit(e)`
**Назначение:** Обработчик отправки формы заказа
**Процесс:**
1. Предотвращение стандартной отправки формы
2. Сбор данных из формы
3. Проверка авторизации
4. Вызов `submitOrder()`
5. Отображение результата пользователю

**Пример:**
```javascript
async function submitOrder(formData, orderType) {
    const title = `${orderType}: ${formData.material}`;
    const requestBody = {
        title: title,
        status: 'новая'
    };
    const response = await fetch(`${API_URL}/orders`, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestBody)
    });
    return await response.json();
}
```

---

### 4. **Работа с костюмами (`costumes.js`)**

#### `loadCostumes()`
**Назначение:** Загрузка списка костюмов
**Процесс:**
1. Отправка GET запроса к `/api/costumes`
2. Получение списка костюмов
3. Отображение в виде карточек (для пользователей)
4. Отображение в таблице (для администраторов)

#### `openModal(costumeId)`
**Назначение:** Открытие модального окна бронирования
**Процесс:**
1. Установка выбранного костюма
2. Установка дат по умолчанию (сегодня и завтра)
3. Отображение модального окна
4. Проверка доступности дат

#### `checkAvailability()`
**Назначение:** Проверка доступности костюма на выбранные даты
**Процесс:**
1. Отправка GET запроса к `/api/costumes/{id}/availability`
2. Получение списка бронирований
3. Проверка конфликтов
4. Отображение статуса доступности
5. Блокировка/разблокировка кнопки бронирования

#### `createReservation()`
**Назначение:** Создание бронирования
**Процесс:**
1. Проверка авторизации
2. Валидация дат
3. Отправка POST запроса к `/api/reservations`
4. Обработка ответа
5. Закрытие модального окна

---

### 5. **Работа с административной панелью (`costumes.js`, `admin-orders.js`)**

#### Функции для администраторов:
- `renderAdminTable(items)` - отображение костюмов в таблице
- `loadAdminReservations()` - загрузка всех бронирований
- `renderAdminReservations(items)` - отображение бронирований
- Обработчики редактирования/удаления костюмов
- Обработчики изменения статуса заказов

**Проверка прав администратора:**
```javascript
// Проверка при загрузке страницы
const prof = await fetch(`${API_URL}/profile`, {
    headers: { 'Authorization': `Bearer ${AuthManager.getToken()}` }
});
const me = await prof.json();
isAdmin = !!me.is_superuser;
if (isAdmin) {
    adminPanel.style.display = 'block';
}
```

---

### 6. **Вспомогательные функции**

#### `showError(message)`
**Назначение:** Отображение сообщения об ошибке
**Процесс:**
- Поиск элемента `error-message`
- Установка текста и стилей
- Отображение сообщения

#### `showSuccess(message)`
**Назначение:** Отображение сообщения об успехе
**Аналогично `showError()`**

#### `apiRequest(url, options)`
**Назначение:** Обертка для HTTP запросов
**Функции:**
- Обработка ошибок
- Парсинг JSON ответа
- Логирование ошибок

---

## База данных и модели

### Структура базы данных

#### 1. **Таблица `users`**
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_superuser BOOLEAN DEFAULT FALSE,
    is_verified BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME
);
```

**Модель SQLAlchemy:**
```python
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

---

#### 2. **Таблица `profiles`**
```sql
CREATE TABLE profiles (
    id INTEGER PRIMARY KEY,
    user_id INTEGER UNIQUE NOT NULL,
    name TEXT,
    phone TEXT,
    age INTEGER,
    photo_filename TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

**Связь:** Один к одному с `users` (один пользователь = один профиль)

---

#### 3. **Таблица `costumes`**
```sql
CREATE TABLE costumes (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    image_filename TEXT NOT NULL,
    price INTEGER NOT NULL,
    available BOOLEAN DEFAULT TRUE
);
```

**Связи:**
- Один ко многим с `orders` (один костюм может быть в нескольких заказах)
- Один ко многим с `reservations` (один костюм может иметь несколько бронирований)

---

#### 4. **Таблица `orders`**
```sql
CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    costume_id INTEGER,
    title TEXT NOT NULL,
    status TEXT DEFAULT 'новая',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (costume_id) REFERENCES costumes(id)
);
```

**Связи:**
- Многие к одному с `users` (один пользователь может иметь много заказов)
- Многие к одному с `costumes` (один костюм может быть в нескольких заказах, опционально)

---

#### 5. **Таблица `reservations`**
```sql
CREATE TABLE reservations (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    costume_id INTEGER NOT NULL,
    date_from DATE NOT NULL,
    date_to DATE NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (costume_id) REFERENCES costumes(id)
);
```

**Связи:**
- Многие к одному с `users`
- Многие к одному с `costumes`

---

### SQL запросы в приложении

#### Пример 1: Получение заказов пользователя
```python
result = await session.execute(
    select(Order)
    .where(Order.user_id == user.id)
    .order_by(Order.created_at.desc())
)
orders = result.scalars().all()
```

#### Пример 2: Получение всех заказов с информацией о пользователе (для админа)
```python
q = (
    select(Order, User, Costume)
    .join(User, User.id == Order.user_id)
    .outerjoin(Costume, Costume.id == Order.costume_id)
    .order_by(Order.created_at.desc())
)
result = await session.execute(q)
```

#### Пример 3: Проверка конфликтов бронирований
```python
q = select(Reservation).where(
    Reservation.costume_id == payload.costume_id,
    Reservation.date_from <= payload.date_to,
    Reservation.date_to >= payload.date_from,
)
result = await session.execute(q)
conflict = result.scalars().first()
```

---

## Аутентификация и авторизация

### JWT токены

#### Процесс аутентификации:

1. **Регистрация/Логин:**
   - Пользователь отправляет email и password
   - Бэкенд проверяет учетные данные
   - Генерируется JWT токен
   - Токен возвращается клиенту

2. **Хранение токена:**
   ```javascript
   // Сохранение после логина
   const { access_token } = await loginResponse.json();
   localStorage.setItem('jwt_token', access_token);
   ```

3. **Использование токена:**
   ```javascript
   // В каждом защищенном запросе
   const token = localStorage.getItem('jwt_token');
   fetch(url, {
       headers: {
           'Authorization': `Bearer ${token}`
       }
   });
   ```

4. **Проверка на бэкенде:**
   ```python
   @app.get("/profile")
   async def get_profile(user: User = Depends(current_active_user)):
       # FastAPI Users автоматически:
       # 1. Извлекает токен из заголовка Authorization
       # 2. Проверяет его валидность
       # 3. Находит пользователя в БД
       # 4. Проверяет что пользователь активен
       # 5. Передает user в функцию
   ```

---

### Уровни доступа

#### 1. **Публичный доступ** (не требует авторизации)
- `GET /api/costumes` - список костюмов
- `POST /api/chat` - публичный чат
- `POST /api/auth/register` - регистрация
- `POST /api/auth/login` - вход

#### 2. **Авторизованный пользователь**
- `GET /api/profile` - профиль
- `PUT /api/profile` - обновление профиля
- `POST /api/orders` - создание заказа
- `GET /api/orders/me` - мои заказы
- `POST /api/reservations` - создание бронирования

#### 3. **Администратор** (`is_superuser = True`)
- `GET /api/orders/all` - все заказы
- `PATCH /api/orders/{id}/status` - изменение статуса
- `POST /api/costumes` - создание костюма
- `PUT /api/costumes/{id}` - обновление костюма
- `DELETE /api/costumes/{id}` - удаление костюма
- `GET /api/reservations/all` - все бронирования
- `DELETE /api/reservations/{id}` - удаление бронирования

---

### Проверка прав администратора

**На бэкенде:**
```python
def require_admin(user: User = Depends(current_active_user)):
    if not user.is_superuser:
        raise HTTPException(status_code=403, detail="Только для администратора")
    return user

@app.delete("/costumes/{id}")
async def delete_costume(user: User = Depends(require_admin)):
    # Только администраторы могут выполнить этот код
```

**На фронтенде:**
```javascript
// Проверка при загрузке страницы
const prof = await fetch(`${API_URL}/profile`, {
    headers: { 'Authorization': `Bearer ${token}` }
});
const me = await prof.json();
if (me.is_superuser) {
    // Показать административную панель
    adminPanel.style.display = 'block';
}
```

---

## Заключение

Данное приложение представляет собой полнофункциональную веб-систему для управления ателье с следующими возможностями:

1. **Управление пользователями** - регистрация, авторизация, профили
2. **Управление заказами** - создание, просмотр, изменение статуса
3. **Каталог костюмов** - просмотр, бронирование, управление (для админов)
4. **Система бронирований** - проверка доступности, создание бронирований
5. **Чат-бот** - автоматические ответы на вопросы клиентов
6. **Административная панель** - управление всеми сущностями

Архитектура построена на принципах REST API с четким разделением между фронтендом и бэкендом, что обеспечивает масштабируемость и удобство поддержки.

