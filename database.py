import sqlite3
from config import DB_NAME

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT,
            run_time TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            completed_count INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

def add_task_to_db(user_id: int, title: str, run_time_str: str) -> int:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tasks (user_id, title, run_time) VALUES (?, ?, ?)", (user_id, title, run_time_str))
    task_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return task_id

def get_task_by_id(task_id: int) -> str:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT title FROM tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else "Задача"

def delete_task_from_db(task_id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()

def increment_user_score(user_id: int) -> int:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, completed_count) VALUES (?, 0)", (user_id,))
    cursor.execute("UPDATE users SET completed_count = completed_count + 1 WHERE user_id = ?", (user_id,))
    cursor.execute("SELECT completed_count FROM users WHERE user_id = ?", (user_id,))
    count = cursor.fetchone()[0]
    conn.commit()
    conn.close()
    return count

def get_user_score(user_id: int) -> int:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT completed_count FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else 0

def get_user_tasks(user_id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, run_time FROM tasks WHERE user_id = ?", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows
def get_all_uncompleted_tasks():
    """Получает все задачи из БД для восстановления при старте бота"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, user_id, title, run_time FROM tasks")
    rows = cursor.fetchall()
    conn.close()
    return rows 
def get_tasks_by_date(user_id: int, date_str: str):
    """Получает задачи на конкретную дату (YYYY-MM-DD)"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, run_time FROM tasks WHERE user_id = ? AND run_time LIKE ?", (user_id, f"{date_str}%"))
    rows = cursor.fetchall()
    conn.close()
    return rows