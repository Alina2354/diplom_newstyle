from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import google.generativeai as genai
import os
import re
import traceback
from dotenv import load_dotenv
import logging
from contextlib import asynccontextmanager
from knowledge_base import knowledge_base
from database import create_tables, get_async_session
from models import User
from auth import fastapi_users, auth_backend, current_active_user
from schemas import UserRead, UserCreate
from sqlalchemy import select
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import status as http_status
from models import Order, Costume, Reservation, Profile
from datetime import date
from typing import List, Optional
from fastapi import UploadFile, File, Form
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import shutil
from pathlib import Path
import uuid


# Создаем абсолютный путь к директории uploads относительно текущего файла
BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "uploads"

pwd_helper = CryptContext(schemes=["bcrypt"], deprecated="auto")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ========== КОД ПРИ ЗАПУСКЕ ПРИЛОЖЕНИЯ ==========
    
    
    from models import User, Profile, Order, Costume, Reservation
    
    logger.info("Создание таблиц базы данных...")
    try:
        await create_tables()
        logger.info("Таблицы базы данных успешно созданы")
    except Exception as e:
        logger.error(f"Ошибка создания таблиц: {str(e)}")
        raise  

   
    super_email = os.getenv("SUPERUSER_EMAIL", "akunishnikova04@bk.ru")
    super_password = os.getenv("SUPERUSER_PASSWORD", "rTpAMA!qo65B")
    
    try:
        async for session in get_async_session():
            result = await session.execute(select(User).where(User.email == super_email))
            su = result.scalar_one_or_none()
            
            if su is None:
                hashed_password = pwd_helper.hash(super_password)
                new_user = User(
                    email=super_email,
                    hashed_password=hashed_password,  
                    is_active=True,      
                    is_superuser=True,  
                    is_verified=True,    
                )
                
                session.add(new_user)
               
                await session.commit()
                await session.refresh(new_user)
                logger.info(f"Создан суперпользователь: {super_email}")
                
            else:
                updated = False
                
                if not su.is_superuser or not su.is_active or not su.is_verified:
                    su.is_superuser = True
                    su.is_active = True
                    su.is_verified = True
                    updated = True  
                
                force_pwd = os.getenv("SUPERUSER_FORCE_PASSWORD", "false").lower() in ("1", "true", "yes")
                if force_pwd:
                    su.hashed_password = pwd_helper.hash(super_password)
                    updated = True
                if updated:
                    await session.commit()  
                    await session.refresh(su)  
                    logger.info(f"Суперпользователь обновлен: {super_email}")
                    
    except Exception as e:
        logger.error(f"Не удалось создать/обновить суперпользователя: {e}")
    yield
    


app = FastAPI(lifespan=lifespan)

# ========== НАСТРОЙКА СТАТИЧЕСКИХ ФАЙЛОВ ==========

# Создаем директорию uploads, если её нет
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

# ========== НАСТРОЙКА CORS (Cross-Origin Resource Sharing) ==========

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# ========== ИНИЦИАЛИЗАЦИЯ GEMINI AI ==========

gemini_api_key = os.getenv("GEMINI_API_KEY")


if not gemini_api_key:
    logger.warning("GEMINI_API_KEY не найден в переменных окружения. Gemini будет отключен.")
    model = None  
else:
    try:
        genai.configure(api_key=gemini_api_key)
        model = genai.GenerativeModel('gemini-flash-2.5')
        logger.info("Gemini успешно инициализирован")
    except Exception as e:
        logger.error(f"Ошибка инициализации Gemini: {str(e)}")
        model = None

# ========== PYDANTIC МОДЕЛИ ДЛЯ ВАЛИДАЦИИ ДАННЫХ ==========

class Message(BaseModel):
    text: str

# ========== ФУНКЦИИ ДЛЯ РАБОТЫ С БАЗОЙ ЗНАНИЙ ==========

def preprocess_text(text: str) -> str:
    text = text.lower().strip()
    
    # re.sub(pattern, replacement, string) - заменяет все совпадения регулярного выражения
    # r'[^\w\s]' - регулярное выражение:
    #   [^...] - любой символ, НЕ входящий в набор
    #   \w - буквы, цифры, подчеркивания (word characters)
    #   \s - пробельные символы (пробел, табуляция, перенос строки)
    #   [^\w\s] - любой символ, который НЕ буква/цифра/пробел (т.е. знаки препинания)
    # Заменяем все знаки препинания на пробел
    # "Привет, мир!" -> "Привет  мир "
    text = re.sub(r'[^\w\s]', ' ', text)
    
    # r'\s+' - регулярное выражение для одного или более пробельных символов подряд
    # Заменяем множественные пробелы на один пробел
    # "Привет    мир" -> "Привет мир"
    text = re.sub(r'\s+', ' ', text)
    
    return text

def find_in_knowledge_base(user_input: str) -> str:
    user_input = preprocess_text(user_input)
    
    # ========== ПРОВЕРКА ПРИВЕТСТВИЙ ==========

    greeting_words = ['привет', 'здравствуй', 'здравствуйте', 'начать', 'start', 'hello', 'hi']
    if any(word in user_input for word in greeting_words) and len(user_input.split()) < 4:
        return knowledge_base["приветствия"]["default"]
    
    # ========== ПРОВЕРКА ОБЩИХ ВОПРОСОВ ==========

    general_questions = ['что ты умеешь', 'что можешь', 'твои возможности', 'функции']
    if any(question in user_input for question in general_questions):
        return "Я могу отвечать на вопросы о работе ателье. Попробуйте спросить о чем-то конкретном!"
    
    # ========== ПОИСК ТОЧНОГО СОВПАДЕНИЯ ТЕРМИНОВ ==========

    for term, definition in knowledge_base["термины"].items():
        if term in user_input:
            return f"📚 {term.upper()}: {definition}"
    
    # ========== ПОИСК ПО КЛЮЧЕВЫМ СЛОВАМ В ВОПРОСАХ ==========

    
    best_match = None  
    max_matches = 0   
    
    for question, answer in knowledge_base["вопросы"].items():
        question_words = set(preprocess_text(question).split())
        input_words = set(user_input.split())
        matches = len(question_words.intersection(input_words))
        if matches > max_matches and matches > 0:
            max_matches = matches
            best_match = answer
   
    if best_match:
        return best_match
    return None

# ========== ПОДКЛЮЧЕНИЕ РОУТЕРОВ FASTAPI USERS ==========

app.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)

# ========== ДОПОЛНИТЕЛЬНЫЙ ПРОСТОЙ ЭНДПОИНТ РЕГИСТРАЦИИ ==========


from fastapi import Request
class RegisterRequest(BaseModel):
    email: str      
    password: str   

from fastapi import status as http_status

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

# ========== ЭНДПОИНТЫ ЧАТА ==========

# Публичный эндпоинт чата (без авторизации)
# Доступен всем пользователям, даже неавторизованным
@app.post("/chat")
async def chat_endpoint(message: Message):
    logger.info(f"Получен вопрос: {message.text}")
    kb_response = find_in_knowledge_base(message.text)
    
    if kb_response:
        logger.info("Ответ найден в базе знаний")
        return {"response": kb_response}
    if model is not None:
        try:
            logger.info("Используем Gemini для генерации ответа")
            prompt = f"""Ты - помощник для клиентов в ателье 'Новый стиль'.
            
           Основные услуги ателье "Новый Стиль":
           1. Ремонт одежды
           2. Пошив одежды
           3. Вышивка
           4. Печать на кружках и предметах одежды

           Общая информация и преимущества "Нового Стиля":

            •  Расположение: Удобное расположение на улице Гагарина 36/1, легко добраться.
            •  Мастера: Команда опытных и квалифицированных мастеров, которые любят свою работу.
            •  Качество: Гарантия высокого качества всех предоставляемых услуг. Мы используем профессиональное оборудование и материалы.
            •  Индивидуальный подход: Внимательное отношение к каждому клиенту и его пожеланиям.
            •  Консультации: Всегда готовы проконсультировать по вопросам выбора материалов, дизайна, возможностей ремонта или пошива.
            •  Сроки: Сроки выполнения работ обсуждаются индивидуально и зависят от сложности заказа и текущей загрузки.
            •  Цены: Конкурентные цены, подробный прайс-лист можно уточнить при личном визите или по телефону.

            
            Если вопрос не по работе или ты не знаешь ответ - вежливо откажись отвечать.
            
            Вопрос: {message.text}
            
            Краткий ответ:"""
            response = model.generate_content(prompt)

            if response.text:
                logger.info("Успешный ответ от Gemini")
                return {"response": response.text}
            else:
                logger.warning("Пустой ответ от Gemini")
                raise Exception("Пустой ответ")
                
        except Exception as e:
            logger.error(f"Ошибка при обращении к Gemini: {str(e)}")
            
    
    
    fallback_responses = [
        "Извините, я не нашел ответа на этот вопрос в базе знаний. Попробуйте переформулировать вопрос.",
        "Этот вопрос пока не добавлен в мою базу знаний.",
        "К сожалению, я не могу ответить на этот вопрос."
    ]
    
    
    import random
    return {"response": random.choice(fallback_responses)}

# Защищенный эндпоинт чата для авторизованных пользователей
# Требует JWT токен, логирует, кто задал вопрос
@app.post("/chat/authenticated")
async def chat_endpoint_authenticated(
    message: Message,
    user: User = Depends(current_active_user)
):
    logger.info(f"Получен вопрос от пользователя {user.email}: {message.text}")
    kb_response = find_in_knowledge_base(message.text)
    
    if kb_response:
        logger.info("Ответ найден в базе знаний")
        return {"response": kb_response}
    if model is not None:
        try:
            logger.info("Используем Gemini для генерации ответа")
            prompt = f"""Ты - помощник для клиентов в ателье 'Новый стиль'.
            
           Основные услуги ателье "Новый Стиль":
           1. Ремонт одежды
           2. Пошив одежды
           3. Вышивка
           4. Печать на кружках и предметах одежды

           Общая информация и преимущества "Нового Стиля":

            •  Расположение: Удобное расположение на улице Гагарина 36/1, легко добраться.
            •  Мастера: Команда опытных и квалифицированных мастеров, которые любят свою работу.
            •  Качество: Гарантия высокого качества всех предоставляемых услуг. Мы используем профессиональное оборудование и материалы.
            •  Индивидуальный подход: Внимательное отношение к каждому клиенту и его пожеланиям.
            •  Консультации: Всегда готовы проконсультировать по вопросам выбора материалов, дизайна, возможностей ремонта или пошива.
            •  Сроки: Сроки выполнения работ обсуждаются индивидуально и зависят от сложности заказа и текущей загрузки.
            •  Цены: Конкурентные цены, подробный прайс-лист можно уточнить при личном визите или по телефону.

            
            Если вопрос не по работе или ты не знаешь ответ - вежливо откажись отвечать.
            
            Вопрос: {message.text}
            
            Краткий ответ:"""
            
            response = model.generate_content(prompt)
            if response.text:
                logger.info("Успешный ответ от Gemini")
                return {"response": response.text}
            else:
                logger.warning("Пустой ответ от Gemini")
                raise Exception("Пустой ответ")
                
        except Exception as e:
            logger.error(f"Ошибка при обращении к Gemini: {str(e)}")
    fallback_responses = [
        "Извините, я не нашел ответа на этот вопрос в базе знаний. Попробуйте переформулировать вопрос или обратитесь к кураторам в бот.",
        "Этот вопрос пока не добавлен в мою базу знаний. Вы можете задать его кураторам через бот.",
        "К сожалению, я не могу ответить на этот вопрос. Обратитесь, пожалуйста, к кураторам для получения помощи."
    ]
    
    import random
    return {"response": random.choice(fallback_responses)}

# ========== PYDANTIC МОДЕЛИ ДЛЯ ЗАЯВОК ==========


class OrderCreate(BaseModel):
    title: str
    status: Optional[str] = 'новая'
    phone: Optional[str] = None
    costume_id: Optional[int] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    def validate_status(self):
        allowed = ["новая", "в обработке", "завершена"]
        if self.status not in allowed:
            raise HTTPException(
                status_code=400, 
                detail=f"Недопустимый статус. Возможные: {allowed}"
            )

class OrderOut(BaseModel):
    id: int              
    title: str          
    status: str          
    created_at: datetime      
    costume_id: int | None = None
    phone: str | None = None
    date_from: date | None = None
    date_to: date | None = None
    
    class Config:
        from_attributes = True

class OrderAdminOut(BaseModel):
    id: int
    user_id: int         
    user_email: str     
    title: str
    status: str
    created_at: datetime
    costume_id: int | None = None
    costume_title: str | None = None
    phone: str | None = None
    date_from: date | None = None
    date_to: date | None = None  


class OrderStatusUpdate(BaseModel):
    status: str  
    def validate_status(self):
        allowed = ["новая", "в обработке", "завершена"]
        if self.status not in allowed:
            raise HTTPException(
                status_code=400, 
                detail=f"Недопустимый статус. Возможные: {allowed}"
            )

# ========== ЭНДПОИНТ ДЛЯ СОЗДАНИЯ НОВОЙ ЗАЯВКИ ==========

@app.post("/orders", response_model=OrderOut, status_code=http_status.HTTP_201_CREATED)
async def create_order(
    order: OrderCreate,
    user: User = Depends(current_active_user),

    session: AsyncSession = Depends(get_async_session)
):

    try:
        logger.info(f"Создание заказа для пользователя {user.id} ({user.email}): {order.title}")
        order.validate_status()
        
        # Если это заказ на бронирование костюма, проверяем конфликты дат
        if order.costume_id is not None and order.date_from is not None and order.date_to is not None:
            costume = await session.get(Costume, order.costume_id)
            
            if not costume:
                raise HTTPException(status_code=404, detail="Костюм не найден")
            
            if not costume.available:
                raise HTTPException(status_code=400, detail="Костюм недоступен для бронирования")
            
            # Проверяем валидность дат
            if order.date_to < order.date_from:
                raise HTTPException(status_code=400, detail="Дата окончания не может быть раньше даты начала")
            
            
            
            # Проверяем конфликты с существующими заказами на бронирование
            q_orders = select(Order).where(
                Order.costume_id == order.costume_id,
                Order.date_from.isnot(None),
                Order.date_to.isnot(None),
                Order.date_from <= order.date_to,
                Order.date_to >= order.date_from
            )
            result_orders = await session.execute(q_orders)
            conflict_order = result_orders.scalars().first()
            if conflict_order:
                raise HTTPException(
                    status_code=409, 
                    detail="Выбранные даты недоступны (пересечение с существующим заказом на бронирование)"
                )
        elif order.costume_id is not None:
            # Если костюм указан, но даты нет - просто проверяем существование костюма
            costume = await session.get(Costume, order.costume_id)
            if not costume:
                raise HTTPException(status_code=404, detail="Костюм не найден")
        
        db_order = Order(
            user_id=user.id,                   
            title=order.title,                  
            status=order.status,                
            costume_id=order.costume_id,
            phone=order.phone,
            date_from=order.date_from,
            date_to=order.date_to
        )
        session.add(db_order)
        await session.commit()
        await session.refresh(db_order)
        
        logger.info(f"Заказ успешно создан: ID={db_order.id}, User ID={db_order.user_id}, Title={db_order.title}")
        
        return db_order
        
    except HTTPException:
        raise
    except Exception as e:
        error_trace = traceback.format_exc()
        logger.error(f"Ошибка создания заказа для пользователя {user.id}: {str(e)}\n{error_trace}")
        raise HTTPException(status_code=500, detail=f"Ошибка создания заказа: {str(e)}")

# ========== ЭНДПОИНТ ДЛЯ ПОЛУЧЕНИЯ ЗАЯВОК ПОЛЬЗОВАТЕЛЯ ==========

@app.get("/orders/me", response_model=List[OrderOut])
async def get_my_orders(

    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
   
    try:
        logger.info(f"Получение заявок для пользователя {user.id} ({user.email})")
        result = await session.execute(
            select(Order)
            .where(Order.user_id == user.id)
            .order_by(Order.created_at.desc())
        )
        orders = result.scalars().all()
        
        logger.info(f"Найдено заявок: {len(orders)}")
        orders_list = [
            OrderOut(
                id=order.id,
                title=order.title,
                status=order.status,
                created_at=str(order.created_at) if order.created_at else "",
                costume_id=order.costume_id,
                phone=order.phone,
                date_from=order.date_from,
                date_to=order.date_to
            )
            for order in orders  
        ]
        
        logger.info(f"Заявки успешно возвращены для пользователя {user.id}")
        return orders_list
        
    except HTTPException:
        raise
    except Exception as e:
        error_trace = traceback.format_exc()
        logger.error(f"Ошибка получения заявок для пользователя {user.id}: {str(e)}\n{error_trace}")
        raise HTTPException(
            status_code=500, 
            detail=f"Ошибка получения заявок: {str(e)}"
        )

# ========== ФУНКЦИЯ-ЗАВИСИМОСТЬ ДЛЯ ПРОВЕРКИ ПРАВ АДМИНИСТРАТОРА ==========

def require_admin(user: User = Depends(current_active_user)):
    if not user.is_superuser:
        raise HTTPException(status_code=403, detail="Только для администратора")
    return user

@app.get("/orders/all", response_model=List[OrderAdminOut])
async def get_all_orders_admin(user: User = Depends(require_admin), session: AsyncSession = Depends(get_async_session)):
    q = (
        select(Order, User, Costume)
        .join(User, User.id == Order.user_id)
        .outerjoin(Costume, Costume.id == Order.costume_id)
        .order_by(Order.created_at.desc())
    )
    result = await session.execute(q)
    items = []
    for order, u, c in result.all():
        items.append(OrderAdminOut(
            id=order.id,
            user_id=u.id,
            user_email=u.email,
            title=order.title,
            status=order.status,
            created_at=str(order.created_at),
            costume_id=order.costume_id,
            costume_title=(c.title if c else None),
            phone=order.phone,
            date_from=order.date_from,
            date_to=order.date_to
        ))
    return items

@app.patch("/orders/{order_id}/status", response_model=OrderOut)
async def update_order_status(order_id: int, payload: OrderStatusUpdate, user: User = Depends(require_admin), session: AsyncSession = Depends(get_async_session)):
    payload.validate_status()
    order = await session.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    order.status = payload.status
    await session.commit()
    await session.refresh(order)
    return order


# ========== ЭНДПОИНТ ДЛЯ ПОЛУЧЕНИЯ ПРОФИЛЯ ПОЛЬЗОВАТЕЛЯ ==========


@app.get("/profile")
async def get_profile(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    try:
        logger.info(f"Получение профиля для пользователя {user.id} ({user.email})")
        result = await session.execute(select(Profile).where(Profile.user_id == user.id))
        prof = result.scalar_one_or_none()
        
        logger.info(f"Профиль найден: {prof is not None}")
        
        
        photo_url = None
        if prof and prof.photo_filename:
            photo_url = f"/uploads/{prof.photo_filename}"
        response_data = {
            "id": user.id,                   
            "email": user.email,             
            "is_active": user.is_active,     
            "is_verified": user.is_verified,  
            "is_superuser": user.is_superuser,  
            "created_at": str(user.created_at) if user.created_at else None,
            "name": (prof.name if prof else None),
            "phone": (prof.phone if prof else None),
            "age": (prof.age if prof else None),
            "photo_url": photo_url,  
        }
        
        logger.info(f"Профиль успешно возвращен для пользователя {user.id}")
        return response_data  
        
    except HTTPException:
        raise
    except Exception as e:
        error_trace = traceback.format_exc()
        logger.error(f"Ошибка получения профиля для пользователя {user.id}: {str(e)}\n{error_trace}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения профиля: {str(e)}")

# ========== PYDANTIC МОДЕЛЬ ДЛЯ ОБНОВЛЕНИЯ ПРОФИЛЯ ==========

class ProfileUpdate(BaseModel):
    name: Optional[str] = None   
    phone: Optional[str] = None  
    age: Optional[int] = None    

# ========== ЭНДПОИНТ ДЛЯ ОБНОВЛЕНИЯ ПРОФИЛЯ ==========

@app.put("/profile")
async def update_profile(
    payload: ProfileUpdate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
   
    try:
        logger.info(f"Обновление профиля для пользователя {user.id} ({user.email})")
        if payload.age is not None:
            if payload.age < 0 or payload.age > 120:
                raise HTTPException(
                    status_code=400, 
                    detail="Возраст должен быть от 0 до 120"
                )
        
        result = await session.execute(
            select(Profile).where(Profile.user_id == user.id)
        )
        prof = result.scalar_one_or_none()
        if prof is None:
            prof = Profile(user_id=user.id)  
            session.add(prof) 
            await session.flush() 
        
        if payload.name is not None:
            name_trimmed = payload.name.strip() if payload.name else ""
            prof.name = name_trimmed if name_trimmed else None
        if payload.phone is not None:
            phone_trimmed = payload.phone.strip() if payload.phone else ""
            prof.phone = phone_trimmed if phone_trimmed else None
        if payload.age is not None:
            prof.age = payload.age
        

        await session.commit()
        await session.refresh(prof) 
        
        logger.info(f"Профиль успешно обновлен для пользователя {user.id}")
        return {"ok": True}
        
    except HTTPException:
        raise
    except Exception as e:
        error_trace = traceback.format_exc()
        logger.error(f"Ошибка обновления профиля для пользователя {user.id}: {str(e)}\n{error_trace}")
        raise HTTPException(status_code=500, detail=f"Ошибка обновления профиля: {str(e)}")

# ========== ЭНДПОИНТ ДЛЯ ЗАГРУЗКИ ФОТОГРАФИИ ПРОФИЛЯ ==========

@app.post("/profile/photo")
async def upload_profile_photo(
    image: UploadFile = File(...),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    ext = os.path.splitext(image.filename)[1].lower()
    if ext not in [".jpg", ".jpeg", ".png"]:
        raise HTTPException(
            status_code=400, 
            detail="Недопустимый формат файла. Только .jpg, .png"
        )

    safe_name = f"user_{user.id}_{image.filename}"
    out_path = UPLOAD_DIR / safe_name
    with open(out_path, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)
    result = await session.execute(
        select(Profile).where(Profile.user_id == user.id)
    )
    prof = result.scalar_one_or_none()
    if prof is None:
        prof = Profile(user_id=user.id)
        session.add(prof)
    prof.photo_filename = safe_name
    await session.commit()
    return {"photo_url": f"/uploads/{safe_name}"}

@app.get("/")
async def root():
    return {
        "message": "Chat API with FastAPI-Users Authentication",
        "version": "2.0",
        "endpoints": {
            "auth": {
                "register": "/auth/register",
                "login": "/auth/login",
                "logout": "/auth/logout",
                "verify": "/auth/verify"
            },
            "chat": {
                "chat": "/chat (public - no authentication required)",
                "chat_authenticated": "/chat/authenticated (requires authentication)"
            },
            "user": {
                "profile": "/profile (requires authentication)",
                "users": "/users (admin only)"
            }
        }
    }

class CostumeCreate(BaseModel):
    title: str
    description: str | None = None
    price: int
    available: bool = True

class CostumeOut(BaseModel):
    id: int
    title: str
    description: str | None
    price: int
    available: bool
    image_url: str
    class Config:
        from_attributes = True

@app.post("/costumes", response_model=CostumeOut)
async def create_costume(
    title: str = Form(...),
    description: str = Form(None),
    price: int = Form(...),
    available: bool = Form(True),
    image: UploadFile = File(...),
    user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_async_session),
):
    # Проверка расширения
    ext = os.path.splitext(image.filename)[1].lower()
    if ext not in [".jpg", ".jpeg", ".png"]:
        raise HTTPException(status_code=400, detail="Недопустимый формат файла. Только .jpg, .png")
    
    # Генерируем уникальное имя файла для избежания конфликтов
    unique_filename = f"{uuid.uuid4()}{ext}"
    out_path = UPLOAD_DIR / unique_filename
    with open(out_path, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)
    costume = Costume(title=title, description=description, price=price, available=available, image_filename=unique_filename)
    session.add(costume)
    await session.commit()
    await session.refresh(costume)
    return {**costume.__dict__, "image_url": f"/uploads/{costume.image_filename}"}

@app.get("/costumes", response_model=list[CostumeOut])
async def list_costumes(session: AsyncSession = Depends(get_async_session)):
    result = await session.execute(select(Costume))
    costumes = result.scalars().all()
    return [{**c.__dict__, "image_url": f"/uploads/{c.image_filename}"} for c in costumes]

@app.get("/costumes/{costume_id}", response_model=CostumeOut)
async def get_costume(costume_id: int, session: AsyncSession = Depends(get_async_session)):
    costume = await session.get(Costume, costume_id)
    if not costume:
        raise HTTPException(status_code=404, detail="Костюм не найден")
    return {**costume.__dict__, "image_url": f"/uploads/{costume.image_filename}"}

@app.put("/costumes/{costume_id}", response_model=CostumeOut)
async def update_costume(
    costume_id: int,
    title: str = Form(...),
    description: str = Form(None),
    price: int = Form(...),
    available: bool = Form(True),
    image: UploadFile = File(None),
    user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_async_session),
):
    costume = await session.get(Costume, costume_id)
    if not costume:
        raise HTTPException(status_code=404, detail="Костюм не найден")
    costume.title = title
    costume.description = description
    costume.price = price
    costume.available = available
    if image is not None:
        ext = os.path.splitext(image.filename)[1].lower()
        if ext not in [".jpg", ".jpeg", ".png"]:
            raise HTTPException(status_code=400, detail="Недопустимый формат файла. Только .jpg, .png")
        
        # Генерируем уникальное имя файла для избежания конфликтов
        unique_filename = f"{uuid.uuid4()}{ext}"
        out_path = UPLOAD_DIR / unique_filename
        
        # Удаляем старое изображение, если оно существует
        if costume.image_filename:
            old_path = UPLOAD_DIR / costume.image_filename
            if old_path.exists():
                try:
                    old_path.unlink()
                except Exception:
                    pass  # Игнорируем ошибки удаления
        
        with open(out_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        costume.image_filename = unique_filename
    await session.commit()
    await session.refresh(costume)
    return {**costume.__dict__, "image_url": f"/uploads/{costume.image_filename}"}

@app.delete("/costumes/{costume_id}")
async def delete_costume(costume_id: int, user: User = Depends(require_admin), session: AsyncSession = Depends(get_async_session)):
    costume = await session.get(Costume, costume_id)
    if not costume:
        raise HTTPException(status_code=404, detail="Костюм не найден")
    await session.delete(costume)
    await session.commit()
    return {"ok": True}

class ReservationOut(BaseModel):
    id: int
    costume_id: int
    date_from: date
    date_to: date
    created_at: str | None = None
    class Config:
        from_attributes = True

class ReservationCreate(BaseModel):
    costume_id: int
    date_from: date
    date_to: date

    def validate(self):
        if self.date_to < self.date_from:
            raise HTTPException(status_code=400, detail="date_to не может быть раньше date_from")

@app.get("/costumes/{costume_id}/availability")
async def costume_availability(costume_id: int, session: AsyncSession = Depends(get_async_session), from_date: date | None = None, to_date: date | None = None):
    """
    Проверяет доступность костюма на указанные даты.
    Проверяет как старые бронирования (Reservations), так и заказы на бронирование (Orders с costume_id и датами).
    """
    conflicts = []
    
    try:
        # Проверяем старые бронирования (Reservations)
        q_reservations = select(Reservation).where(Reservation.costume_id == costume_id)
        if from_date is not None and to_date is not None:
            q_reservations = q_reservations.where(
                Reservation.date_from <= to_date, 
                Reservation.date_to >= from_date
            )
        result_reservations = await session.execute(q_reservations)
        reservations = result_reservations.scalars().all()
        
        for res in reservations:
            conflicts.append({
                "id": res.id,
                "type": "reservation",
                "date_from": str(res.date_from),
                "date_to": str(res.date_to)
            })
        
        # Проверяем заказы на бронирование (Orders с costume_id и датами)
        q_orders = select(Order).where(
            Order.costume_id == costume_id
        ).where(
            Order.date_from.isnot(None)
        ).where(
            Order.date_to.isnot(None)
        )
        if from_date is not None and to_date is not None:
            q_orders = q_orders.where(
                Order.date_from <= to_date,
                Order.date_to >= from_date
            )
        result_orders = await session.execute(q_orders)
        orders = result_orders.scalars().all()
        
        for order in orders:
            conflicts.append({
                "id": order.id,
                "type": "order",
                "date_from": str(order.date_from),
                "date_to": str(order.date_to)
            })
        
        return conflicts
        
    except Exception as e:
        logger.error(f"Ошибка при проверке доступности костюма {costume_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка проверки доступности: {str(e)}")

@app.post("/reservations", response_model=ReservationOut, status_code=http_status.HTTP_201_CREATED)
async def create_reservation(payload: ReservationCreate, user: User = Depends(current_active_user), session: AsyncSession = Depends(get_async_session)):
    payload.validate()
    costume = await session.get(Costume, payload.costume_id)
    if not costume or not costume.available:
        raise HTTPException(status_code=404, detail="Костюм недоступен или не найден")

    q = select(Reservation).where(
        Reservation.costume_id == payload.costume_id,
        Reservation.date_from <= payload.date_to,
        Reservation.date_to >= payload.date_from,
    )
    result = await session.execute(q)
    conflict = result.scalars().first()
    if conflict:
        raise HTTPException(status_code=409, detail="Выбранные даты недоступны (пересечение с существующим бронированием)")
    res = Reservation(
        user_id=user.id,
        costume_id=payload.costume_id,
        date_from=payload.date_from,
        date_to=payload.date_to,
    )
    session.add(res)
    await session.commit()
    await session.refresh(res)
    return res

@app.get("/reservations/me", response_model=list[ReservationOut])
async def my_reservations(user: User = Depends(current_active_user), session: AsyncSession = Depends(get_async_session)):
    result = await session.execute(select(Reservation).where(Reservation.user_id == user.id).order_by(Reservation.date_from.desc()))
    return result.scalars().all()

class ReservationAdminOut(BaseModel):
    id: int
    user_id: int
    user_email: str
    costume_id: int
    costume_title: str
    date_from: date
    date_to: date
    created_at: str | None = None

@app.get("/reservations/all", response_model=List[ReservationAdminOut])
async def all_reservations_admin(user: User = Depends(require_admin), session: AsyncSession = Depends(get_async_session)):
    q = (
        select(Reservation, User, Costume)
        .join(User, User.id == Reservation.user_id)
        .join(Costume, Costume.id == Reservation.costume_id)
        .order_by(Reservation.date_from.desc())
    )
    result = await session.execute(q)
    items = []
    for r, u, c in result.all():
        items.append(ReservationAdminOut(
            id=r.id,
            user_id=u.id,
            user_email=u.email,
            costume_id=c.id,
            costume_title=c.title,
            date_from=r.date_from,
            date_to=r.date_to,
            created_at=str(r.created_at) if r.created_at else None,
        ))
    return items

@app.delete("/reservations/{reservation_id}")
async def delete_reservation_admin(reservation_id: int, user: User = Depends(require_admin), session: AsyncSession = Depends(get_async_session)):
    res = await session.get(Reservation, reservation_id)
    if not res:
        raise HTTPException(status_code=404, detail="Бронь не найдена")
    await session.delete(res)
    await session.commit()
    return {"ok": True}

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)