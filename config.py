# config.py - Конфигурация системы
import os
from datetime import timedelta

class Config:
    # Безопасность
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secure-secret-key-change-in-production')
    SESSION_TIMEOUT = timedelta(hours=8)
    MAX_LOGIN_ATTEMPTS = 5
    PASSWORD_MIN_LENGTH = 8
    
    # База данных
    DATABASE_PATH = 'trade_enterprise.db'
    BACKUP_PATH = 'backups/'
    BACKUP_RETENTION_DAYS = 30
    
    # Права доступа
    ROLE_PERMISSIONS = {
        'admin': {
            'description': 'Полный доступ ко всем функциям',
            'permissions': ['all']
        },
        'manager': {
            'description': 'Управление клиентами, товарами и заказами',
            'permissions': ['view', 'create', 'edit', 'delete', 'manage_content']
        },
        'content_manager': {
            'description': 'Управление контентом сайта',
            'permissions': ['view', 'create_content', 'edit_content', 'publish_content']
        },
        'cashier': {
            'description': 'Работа с кассой, создание заказов',
            'permissions': ['view', 'create_orders', 'edit_own_orders']
        },
        'viewer': {
            'description': 'Только просмотр',
            'permissions': ['view']
        }
    }
    
    # Соответствие ФЗ-152
    PERSONAL_DATA_RETENTION_YEARS = 5
    CONSENT_REQUIRED = True
    LOG_ALL_ACCESS = True
    
    # Настройки приложения
    APP_NAME = "Торговая система предприятия"
    COMPANY_NAME = "Торговое предприятие"
    DEFAULT_CURRENCY = "RUB"
    
    # Пути
    TEMPLATE_FOLDERS = {
        'web': 'templates/',
        'reports': 'reports/'
    }
    
    # Настройки безопасности
    REQUIRE_HTTPS = False  # В production установите True
    CORS_ORIGINS = ['http://localhost:5000']
    
    @staticmethod
    def init_app():
        """Инициализация приложения"""
        # Создаем необходимые директории
        os.makedirs(Config.BACKUP_PATH, exist_ok=True)
        os.makedirs('logs', exist_ok=True)