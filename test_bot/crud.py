from db import get_database_connection
import uuid
import logging

# Функция для сохранения обращения клиента
def save_client_request(user_id, content_type=None, content=None):
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

    # Вставка данных в таблицу client_requests
    cursor.execute(f'''
    INSERT INTO client_requests (request_id, user_id, {content_field})
    VALUES (?, ?, ?)
    ''', (request_id, user_id, content))

    conn.commit()
    conn.close()

    return request_id  # Возвращаем request_id для дальнейшего использования


# Функция для получения данных обращения по request_id
def get_client_request(request_id):
    conn = get_database_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM client_requests WHERE request_id = ?", (request_id,))
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
    cursor.execute("SELECT COUNT(1) FROM client_requests WHERE request_id = ?", (request_id,))
    exists = cursor.fetchone()[0]

    if not exists:
        logging.error(f"Запрос с ID {request_id} не найден в базе данных.")
        conn.close()
        return False

    # Формируем SQL-запрос
    set_clause = ', '.join(f"{field} = ?" for field in fields.keys())
    values = list(fields.values()) + [request_id]

    try:
        cursor.execute(f'''
        UPDATE client_requests SET {set_clause} WHERE request_id = ?
        ''', values)
        conn.commit()
        logging.info(f"Запрос с ID {request_id} успешно обновлен: {fields}")
    except Exception as e:
        logging.error(f"Ошибка при обновлении запроса с ID {request_id}: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

    return True

# def update_client_request(request_id, **fields):
#     conn = get_database_connection()
#     cursor = conn.cursor()
#     set_clause = ', '.join(f"{field} = ?" for field in fields.keys())
#     values = list(fields.values()) + [request_id]
#     cursor.execute(f'''
#     UPDATE client_requests SET {set_clause} WHERE request_id = ?
#     ''', values)
#     conn.commit()
#     conn.close()

