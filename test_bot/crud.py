import uuid
import logging
from psycopg2 import sql

from db import get_database_connection


# Функция для сохранения обращения клиента
def save_client_request(user_id, content_type=None, content=None, branch=None):
    conn = get_database_connection()
    cursor = conn.cursor()
    request_id = str(uuid.uuid4())  # Генерируем уникальный request_id

    # Определяем, какое поле заполнить (текст, фото или видео)
    content_field = None
    if content_type == "text":
        content_field = "content"
    elif content_type == "photo":
        content_field = "photo_id"
    elif content_type == "video":
        content_field = "video_id"
    else:
        content_field = "content"  # Или какое-то другое значение по умолчанию, если тип не определён

    # Если content_field не установлен, выводим ошибку, но разрешаем сохранить без него
    if content_field is None:
        logging.error("Не удалось определить тип содержимого для сохранения.")
        return None  # Если вы не хотите сохранять, если тип не определён

    # Вставка данных в таблицу client_requests
    try:
        cursor.execute(
            sql.SQL("INSERT INTO client_requests (request_id, user_id, {field}, branch) VALUES (%s, %s, %s, %s)")
            .format(field=sql.Identifier(content_field)),
            (request_id, user_id, content if content else None, branch)  # Позволяем content быть None
        )
        conn.commit()
        logging.info(f"Запрос успешно сохранен с request_id: {request_id}")
    except Exception as e:
        logging.error(f"Ошибка при сохранении обращения клиента: {e}")
        conn.rollback()
        request_id = None  # Возвращаем None, если произошла ошибка
    finally:
        conn.close()

    return request_id


# Функция для получения данных обращения по request_id
def get_client_request(request_id):
    conn = get_database_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM client_requests WHERE request_id = %s", (request_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "request_id": row[0],
            "user_id": row[1],
            "content": row[2],
            "photo_id": row[3],
            "video_id": row[4],
            "branch": row[5],
            "created_at": row[6],
            "admin_response": row[7]
        }
    return None


def update_client_request(request_id, **fields):
    conn = get_database_connection()
    cursor = conn.cursor()

    # Проверяем, существует ли запрос с указанным request_id
    cursor.execute("SELECT COUNT(1) FROM client_requests WHERE request_id = %s", (request_id,))
    exists = cursor.fetchone()[0]

    if not exists:
        logging.error(f"Запрос с ID {request_id} не найден в базе данных.")
        conn.close()
        return False

    # Формируем SQL-запрос
    set_clause = ', '.join(f"{field} = %s" for field in fields.keys())
    values = list(fields.values()) + [request_id]

    try:
        cursor.execute(
            sql.SQL("UPDATE client_requests SET " + set_clause + " WHERE request_id = %s"),
            values
        )
        conn.commit()
        logging.info(f"Запрос с ID {request_id} успешно обновлен: {fields}")
    except Exception as e:
        logging.error(f"Ошибка при обновлении запроса с ID {request_id}: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

    return True



