import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SECRET_KEY = 'bandothue-secret-key-2026'
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB

# MySQL
DB_HOST = '127.0.0.1'
DB_USER = 'root'
DB_PASSWORD = ''
DB_NAME = 'bandothue'
DB_CHARSET = 'utf8mb4'
