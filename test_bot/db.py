import psycopg2
from dotenv import load_dotenv
import os

# Загрузка переменных окружения
load_dotenv()


# Функция для получения соединения с базой данных
def get_database_connection():
    conn = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST"),
        port=os.getenv("POSTGRES_PORT"),
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD")
    )
    return conn  # Возвращаем соединение без создания таблицы


# Функция для инициализации базы данных (создание таблиц)
def init_database():
    conn = get_database_connection()
    cursor = conn.cursor()

    # SQL для создания таблицы client_requests, если она не существует
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS client_requests (
        request_id UUID PRIMARY KEY,
        user_id BIGINT,
        content TEXT,
        photo_id TEXT,
        video_id TEXT,
        branch TEXT,
        timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
        admin_response TEXT
    );
    ''')

    # Закрытие курсора и соединения
    conn.commit()
    cursor.close()
    conn.close()


