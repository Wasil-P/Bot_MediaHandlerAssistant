import psycopg2
from psycopg2 import OperationalError
from dotenv import load_dotenv
import os

# Загрузка переменных окружения
load_dotenv()

# Функция для получения соединения с базой данных
def get_database_connection():
    try:
        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST"),
            port=os.getenv("POSTGRES_PORT"),
            dbname=os.getenv("POSTGRES_DB"),
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD")
        )
        return conn  # Возвращаем соединение
    except OperationalError as e:
        print("Ошибка соединения с базой данных:", e)
        return None

# Функция для инициализации базы данных (создание таблиц)
def init_database():
    conn = get_database_connection()
    if conn is None:
        print("Не удалось установить соединение с базой данных.")
        return

    try:
        cursor = conn.cursor()

        # SQL для создания таблицы requests
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS requests (
            request_id SERIAL PRIMARY KEY,          -- Уникальный идентификатор обращения
            user_id BIGINT NOT NULL,                -- Идентификатор клиента
            branch TEXT,                            -- Выбранный филиал
            timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP, -- Дата и время создания обращения
            admin_response TEXT                     -- Ответ администратора
        );
        ''')

        # SQL для создания таблицы request_items
        cursor.execute('''
        CREATE EXTENSION IF NOT EXISTS "uuid-ossp";  -- Убедимся, что расширение UUID доступно

        CREATE TABLE IF NOT EXISTS request_items (
        item_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),   -- Уникальный идентификатор элемента с авто-генерацией UUID
        request_id INT REFERENCES requests(request_id) ON DELETE CASCADE,  -- Связь с таблицей requests
        content_type TEXT CHECK (content_type IN ('text', 'photo', 'video', 'voice')), -- Тип содержимого
        content TEXT,                           -- Текст или ID файла для фото/видео
        timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP  -- Дата и время добавления элемента
);
        ''')

        conn.commit()
    except Exception as e:
        print("Ошибка при инициализации базы данных:", e)
    finally:
        cursor.close()
        conn.close()