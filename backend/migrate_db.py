import asyncio
import sqlite3
from sqlalchemy import text
from database import engine, AsyncSessionLocal

async def migrate_orders_table():
    """
    Добавляет колонку costume_id в таблицу orders, если её нет
    """
    async with AsyncSessionLocal() as session:
        try:
            
            result = await session.execute(text("SELECT costume_id FROM orders LIMIT 1"))
            result.fetchone()
            print("✅ Колонка costume_id уже существует в таблице orders")
            return True
        except Exception as e:
            error_msg = str(e).lower()
            
            if "no such column" in error_msg or "costume_id" in error_msg:
                print("⚠️  Колонка costume_id отсутствует в таблице orders")
                print("🔄 Добавляю колонку costume_id...")
                
                try:
                    # Добавляем колонку costume_id
                    await session.execute(text("""
                        ALTER TABLE orders 
                        ADD COLUMN costume_id INTEGER
                    """))
                    await session.commit()
                    print("✅ Колонка costume_id успешно добавлена")
                    return True
                except Exception as e2:
                    # Если таблицы нет вообще, создадим её заново
                    if "no such table" in str(e2).lower():
                        print("⚠️  Таблица orders не существует, будет создана при следующем запуске")
                        return True
                    print(f"❌ Ошибка при добавлении колонки: {e2}")
                    await session.rollback()
                    return False
            else:
                # Другая ошибка - возможно таблицы нет
                print(f"⚠️  Предупреждение: {e}")
                print("ℹ️  Таблица orders будет создана при следующем запуске приложения")
                return True

async def check_and_fix_all_tables():
    print("=" * 60)
    print("🔄 Проверка и миграция базы данных...")
    print("=" * 60)
    
    success = True
    
    # Мигрируем таблицу orders
    if not await migrate_orders_table():
        success = False
    
    print("=" * 60)
    if success:
        print("✅ Миграция завершена успешно!")
    else:
        print("❌ Миграция завершена с ошибками")
    print("=" * 60)
    
    return success

async def main():
    """Главная функция"""
    try:
        await check_and_fix_all_tables()
    except Exception as e:
        print(f"❌ Критическая ошибка при миграции: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())



