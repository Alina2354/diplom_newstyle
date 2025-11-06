from fastapi_users import FastAPIUsers
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,
)

from fastapi_users.db import SQLAlchemyUserDatabase
from fastapi_users.manager import BaseUserManager
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext
from fastapi import Depends
import os
from typing import Optional
from models import User
from database import get_async_session

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET = os.getenv("SECRET_KEY", "your-secret-key-change-in-production-to-secure-random-string")
bearer_transport = BearerTransport(tokenUrl="auth/login")


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=SECRET, lifetime_seconds=3600)

auth_backend = AuthenticationBackend(
    name="jwt", 
    transport=bearer_transport,  
    get_strategy=get_jwt_strategy,  
)

class UserManager(BaseUserManager[User, int]):
    reset_password_token_secret = SECRET
    verification_token_secret = SECRET

    def parse_id(self, value) -> int:
        if isinstance(value, int):
            return value
        if value is None:
            raise ValueError("ID пользователя не может быть None")
        try:
            return int(value)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Невозможно преобразовать ID пользователя в число: {value}") from e

    async def on_after_register(self, user: User, request=None):
        print(f"User {user.id} has registered.")

    
    async def on_after_forgot_password(self, user: User, token: str, request=None):
        print(f"User {user.id} has forgot their password. Reset token: {token}")

   
    async def on_after_request_verify(self, user: User, token: str, request=None):
        print(f"Verification requested for user {user.id}. Verification token: {token}")


async def get_user_db():
    async for session in get_async_session():
        yield SQLAlchemyUserDatabase(session, User)

async def get_user_manager(user_db: SQLAlchemyUserDatabase = Depends(get_user_db)):
    yield UserManager(user_db)


fastapi_users = FastAPIUsers[User, int](
    get_user_manager,  
    [auth_backend],   
)

current_active_user = fastapi_users.current_user(active=True)
