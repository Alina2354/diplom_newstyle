import sqlite3
from passlib.context import CryptContext

DB_PATH = r'backend/chat_app.db'
EMAIL = 'akunishnikova04@bk.ru'
PASSWORD = 'rTpAMA!qo65B'

pwd_helper = CryptContext(schemes=["bcrypt"], deprecated="auto")
hashed = pwd_helper.hash(PASSWORD)

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

c.execute("SELECT id FROM users WHERE email=?", (EMAIL,))
row = c.fetchone()

if row:
    c.execute(
        "UPDATE users SET hashed_password=?, is_active=1, is_superuser=1, is_verified=1 WHERE email=?",
        (hashed, EMAIL),
    )
else:
    c.execute(
        "INSERT INTO users (email, hashed_password, is_active, is_superuser, is_verified) VALUES (?,?,?,?,?)",
        (EMAIL, hashed, 1, 1, 1),
    )

conn.commit()
conn.close()
print("Superuser ensured:", EMAIL)