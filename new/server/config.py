import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # SEC-01: Enforce secure SECRET_KEY in production
    if os.environ.get('FLASK_ENV') == 'production':
        SECRET_KEY = os.environ.get('SECRET_KEY')
        if not SECRET_KEY or SECRET_KEY == 'dev-secret-key-change-in-prod-please':
            raise ValueError("FATAL: SECRET_KEY is not set or is using the default development key in a production environment.")
    else:
        SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-prod-please'

    if os.environ.get('FLASK_ENV') == 'production':
        if not os.environ.get('DATABASE_URL'):
            raise ValueError("FATAL: DATABASE_URL is not set in a production environment.")

    ALLOWED_ORIGINS = os.environ.get('ALLOWED_ORIGINS', 'http://localhost:5173,http://localhost:5174,http://localhost:5175,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:5174,http://127.0.0.1:5175,http://127.0.0.1:3000').split(',')
    
    # Database Configuration
    # Defaults to SQLite, can be overridden by DB_TYPE env var
    DB_TYPE = os.environ.get('DB_TYPE', 'sqlite')
    
    if DB_TYPE == 'postgres':
        # Ensure your DATABASE_URL is set in .env
        # Example: postgresql://user:password@localhost:5432/ghg_db
        SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
        if not SQLALCHEMY_DATABASE_URI:
             raise ValueError("DB_TYPE is set to postgres but DATABASE_URL is missing!")
    else:
        # Default SQLite
        BASE_DIR = os.path.abspath(os.path.dirname(__file__))
        SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
            'sqlite:///' + os.path.join(BASE_DIR, 'ghg_app.db')

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session Configuration
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    # Only set Secure in production to allow localhost testing
    SESSION_COOKIE_SECURE = os.environ.get('FLASK_ENV') == 'production'

    # CSRF Configuration
    # Set CSRF time limit to None so it lives as long as the session
    # Fixes: 'The CSRF token has expired' for long-running SPA sessions
    WTF_CSRF_TIME_LIMIT = None

    # API-03 FIX: Hard limit on all incoming request bodies — prevents large-payload DoS
    MAX_CONTENT_LENGTH = 1024 * 1024 * 1024  # 1 GB

