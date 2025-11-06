from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

DATABASE_URL = "sqlite+aiosqlite:///./chat_app.db"

engine = create_async_engine(
    DATABASE_URL,  
    connect_args={"check_same_thread": False},  
    echo=True,  
)


AsyncSessionLocal = async_sessionmaker(
    engine, 
    class_=AsyncSession,  
    expire_on_commit=False, 
    autocommit=False,  
    autoflush=True, 
)

Base = declarative_base()


async def get_async_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await migrate_missing_columns()


async def migrate_missing_columns():
    from sqlalchemy import text
    
    async with AsyncSessionLocal() as session:
        try:
            # Проверка и добавление costume_id
            try:
                result = await session.execute(text("SELECT costume_id FROM orders LIMIT 1"))
                result.fetchone()
            except Exception as e:
                error_msg = str(e).lower()
                if "no such column" in error_msg and "costume_id" in error_msg:
                    print("🔄 Добавляю недостающую колонку costume_id в таблицу orders...")
                    await session.execute(text("""
                        ALTER TABLE orders 
                        ADD COLUMN costume_id INTEGER
                    """))
                    await session.commit()
                    print("✅ Колонка costume_id успешно добавлена в таблицу orders")
                elif "no such table" in error_msg:
                    pass
                else:
                    print(f"⚠️  Предупреждение при проверке колонки costume_id: {e}")
            
            # Проверка и добавление phone
            try:
                result = await session.execute(text("SELECT phone FROM orders LIMIT 1"))
                result.fetchone()
            except Exception as e:
                error_msg = str(e).lower()
                if "no such column" in error_msg and "phone" in error_msg:
                    print("🔄 Добавляю недостающую колонку phone в таблицу orders...")
                    await session.execute(text("""
                        ALTER TABLE orders 
                        ADD COLUMN phone TEXT
                    """))
                    await session.commit()
                    print("✅ Колонка phone успешно добавлена в таблицу orders")
                elif "no such table" in error_msg:
                    pass
                else:
                    print(f"⚠️  Предупреждение при проверке колонки phone: {e}")
            
            # Проверка и добавление date_from
            try:
                result = await session.execute(text("SELECT date_from FROM orders LIMIT 1"))
                result.fetchone()
            except Exception as e:
                error_msg = str(e).lower()
                if "no such column" in error_msg and "date_from" in error_msg:
                    print("🔄 Добавляю недостающую колонку date_from в таблицу orders...")
                    await session.execute(text("""
                        ALTER TABLE orders 
                        ADD COLUMN date_from DATE
                    """))
                    await session.commit()
                    print("✅ Колонка date_from успешно добавлена в таблицу orders")
                elif "no such table" in error_msg:
                    pass
                else:
                    print(f"⚠️  Предупреждение при проверке колонки date_from: {e}")
            
            # Проверка и добавление date_to
            try:
                result = await session.execute(text("SELECT date_to FROM orders LIMIT 1"))
                result.fetchone()
            except Exception as e:
                error_msg = str(e).lower()
                if "no such column" in error_msg and "date_to" in error_msg:
                    print("🔄 Добавляю недостающую колонку date_to в таблицу orders...")
                    await session.execute(text("""
                        ALTER TABLE orders 
                        ADD COLUMN date_to DATE
                    """))
                    await session.commit()
                    print("✅ Колонка date_to успешно добавлена в таблицу orders")
                elif "no such table" in error_msg:
                    pass
                else:
                    print(f"⚠️  Предупреждение при проверке колонки date_to: {e}")
        except Exception as e:
            print(f"⚠️  Предупреждение при миграции: {e}")
            try:
                await session.rollback()
            except:
                pass