"""utils/auth_helper.py - User registration and authentication helpers."""

from werkzeug.security import generate_password_hash, check_password_hash
from database import get_connection

USER_DOMAIN = "userjsw"


def normalize_username(username: str) -> str:
    username = (username or "").strip().lower()
    if not username:
        return ""
    local = username.split("@")[0]
    return f"{local}@{USER_DOMAIN}"


def create_user(username: str, password: str) -> str:
    username = normalize_username(username)
    if not username or not password:
        raise ValueError("Username and password are required")
    password_hash = generate_password_hash(password)
    conn = get_connection()
    try:
        with conn.cursor() as c:
            c.execute(
                "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
                (username, password_hash)
            )
        conn.commit()
    finally:
        conn.close()
    return username


def get_user_by_username(username: str):
    username = normalize_username(username)
    conn = get_connection()
    try:
        with conn.cursor() as c:
            c.execute("SELECT * FROM users WHERE username=%s", (username,))
            return c.fetchone()
    finally:
        conn.close()


def verify_password(username: str, password: str) -> bool:
    user = get_user_by_username(username)
    if not user:
        return False
    return check_password_hash(user["password_hash"], password)
