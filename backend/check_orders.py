import sqlite3

conn = sqlite3.connect('chat_app.db')
cursor = conn.cursor()


cursor.execute("PRAGMA table_info(orders)")
columns = cursor.fetchall()
print("Структура таблицы orders:")
for col in columns:
    print(f"  {col[1]} ({col[2]})")

print("\n" + "="*60)
print("Все заказы в БД:")
print("="*60)

try:
    cursor.execute("SELECT id, user_id, title, status, created_at, costume_id FROM orders")
    rows = cursor.fetchall()
    if rows:
        for row in rows:
            print(f"ID: {row[0]}, User ID: {row[1]}, Title: {row[2]}, Status: {row[3]}, Created: {row[4]}, Costume ID: {row[5]}")
    else:
        print("Заказов нет в базе данных")
except Exception as e:
    print(f"Ошибка: {e}")

print("\n" + "="*60)
print("Пользователи в БД:")
print("="*60)
try:
    cursor.execute("SELECT id, email FROM users")
    users = cursor.fetchall()
    for user in users:
        print(f"User ID: {user[0]}, Email: {user[1]}")
except Exception as e:
    print(f"Ошибка: {e}")

conn.close()



