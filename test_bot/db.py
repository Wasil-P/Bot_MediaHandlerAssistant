import sqlite3


# Создание таблицы для хранения данных клиента, если она не существует
def get_database_connection():
    conn = sqlite3.connect("tg_bot.db")
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS client_requests (
        request_id TEXT PRIMARY KEY,
        user_id INTEGER,
        content TEXT,
        photo_id TEXT,
        video_id TEXT,
        branch TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        admin_response TEXT
    );
    ''')

    conn.commit()

    # Вернем открытое соединение, чтобы оно могло быть использовано
    return conn


