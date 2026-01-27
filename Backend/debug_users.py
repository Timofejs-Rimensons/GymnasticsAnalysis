
import os
import psycopg2
from psycopg2.extras import RealDictCursor

def list_users():
    url = os.getenv("DATABASE_URL")
    print(f"Connecting to {url}")
    try:
        conn = psycopg2.connect(url)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT id, email, password_hash, created_at FROM users")
        users = cursor.fetchall()
        print(f"Found {len(users)} users:")
        for u in users:
            print(f" - {u['email']} (ID: {u['id']}) Hash: {u['password_hash'][:10]}...")
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_users()
