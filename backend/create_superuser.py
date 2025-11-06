import argparse
import os
import sqlite3
from passlib.context import CryptContext


def get_db_path() -> str:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(current_dir, 'chat_app.db')


def ensure_superuser(email: str, password: str) -> None:
    pwd_helper = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hashed_password = pwd_helper.hash(password)

    db_path = get_db_path()
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS users (\n"
                    "id INTEGER PRIMARY KEY AUTOINCREMENT,\n"
                    "email TEXT UNIQUE NOT NULL,\n"
                    "hashed_password TEXT NOT NULL,\n"
                    "is_active INTEGER NOT NULL DEFAULT 1,\n"
                    "is_superuser INTEGER NOT NULL DEFAULT 0,\n"
                    "is_verified INTEGER NOT NULL DEFAULT 0,\n"
                    "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,\n"
                    "updated_at TIMESTAMP\n"
                    ")")

        cur.execute("SELECT id FROM users WHERE email=?", (email,))
        row = cur.fetchone()
        if row:
            cur.execute(
                "UPDATE users SET hashed_password=?, is_active=1, is_superuser=1, is_verified=1 WHERE email=?",
                (hashed_password, email),
            )
            print(f"Updated existing superuser: {email}")
        else:
            cur.execute(
                "INSERT INTO users (email, hashed_password, is_active, is_superuser, is_verified) VALUES (?,?,?,?,?)",
                (email, hashed_password, 1, 1, 1),
            )
            print(f"Created new superuser: {email}")
        conn.commit()
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Create or update a superuser in chat_app.db")
    parser.add_argument("--email", required=True, help="Email of the superuser")
    parser.add_argument("--password", required=True, help="Password of the superuser")
    args = parser.parse_args()

    ensure_superuser(args.email, args.password)


if __name__ == "__main__":
    main()


