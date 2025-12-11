# security.py - Модуль безопасности
import re
import logging
from datetime import datetime, timedelta
import hashlib
import secrets

class SecurityManager:
    def __init__(self, db):
        self.db = db
        self.setup_logging()
    
    def setup_logging(self):
        """Настройка логирования безопасности"""
        security_logger = logging.getLogger('security')
        security_logger.setLevel(logging.INFO)
        
        handler = logging.FileHandler('security.log')
        formatter = logging.Formatter('%(asctime)s - SECURITY - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        security_logger.addHandler(handler)
    
    def validate_input(self, input_str: str, input_type: str) -> tuple:
        """Валидация входных данных"""
        if not input_str:
            return False, "Пустое значение"
        
        input_str = str(input_str).strip()
        
        patterns = {
            'phone': r'^\+?[1-9]\d{7,14}$',
            'email': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
            'name': r'^[a-zA-Zа-яА-ЯёЁ\s\-]{2,100}$',
            'sku': r'^[A-Z0-9\-]{3,20}$',
            'price': r'^\d+(\.\d{1,2})?$',
            'integer': r'^\d+$',
            'username': r'^[a-zA-Z0-9_]{3,50}$'
        }
        
        sanitization_rules = {
            'html': lambda x: re.sub(r'<[^>]*>', '', x),
            'sql': lambda x: re.sub(r'[\'\";]', '', x),
            'general': lambda x: re.sub(r'[<>\"\']', '', x)
        }
        
        if input_type in patterns:
            if not re.match(patterns[input_type], input_str):
                return False, f"Неверный формат {input_type}"
        
        # Применяем санитизацию
        if input_type in ['name', 'address', 'notes']:
            input_str = sanitization_rules['general'](input_str)
        elif input_type in ['content']:
            input_str = sanitization_rules['html'](input_str)
        
        return True, input_str
    
    def check_password_strength(self, password: str) -> dict:
        """Проверка сложности пароля"""
        checks = {
            'length': len(password) >= 8,
            'uppercase': bool(re.search(r'[A-ZА-Я]', password)),
            'lowercase': bool(re.search(r'[a-zа-я]', password)),
            'digits': bool(re.search(r'\d', password)),
            'special': bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', password)),
            'no_username': True,  # Пароль не должен содержать логин
            'no_common': password not in ['password', '123456', 'qwerty']
        }
        
        score = sum(checks.values())
        
        return {
            'score': score,
            'checks': checks,
            'is_strong': score >= 5,
            'message': 'Слабый пароль' if score < 5 else 'Надежный пароль'
        }
    
    def sanitize_sql_input(self, input_str: str) -> str:
        """Базовая санитизация SQL-ввода"""
        # Используйте параметризованные запросы вместо этой функции!
        dangerous = [';', '--', '/*', '*/', 'xp_', 'union', 'select', 'insert', 
                     'delete', 'update', 'drop', 'alter', 'create', 'exec']
        
        input_lower = input_str.lower()
        for danger in dangerous:
            if danger in input_lower:
                logging.getLogger('security').warning(
                    f"Обнаружена потенциальная SQL-инъекция: {input_str}"
                )
                raise ValueError("Недопустимые символы в запросе")
        
        return input_str
    
    def validate_personal_data(self, data: dict) -> tuple:
        """Валидация персональных данных по ФЗ-152"""
        required_fields = ['full_name']
        errors = []
        
        for field in required_fields:
            if field not in data or not data[field]:
                errors.append(f"Поле {field} обязательно")
        
        # Проверка email
        if 'email' in data and data['email']:
            valid, _ = self.validate_input(data['email'], 'email')
            if not valid:
                errors.append("Неверный формат email")
        
        # Проверка телефона
        if 'phone' in data and data['phone']:
            valid, _ = self.validate_input(data['phone'], 'phone')
            if not valid:
                errors.append("Неверный формат телефона")
        
        # Проверка согласия на обработку данных
        if not data.get('personal_data_consent'):
            errors.append("Требуется согласие на обработку персональных данных")
        
        return len(errors) == 0, errors
    
    def generate_secure_token(self, length: int = 32) -> str:
        """Генерация безопасного токена"""
        return secrets.token_urlsafe(length)
    
    def hash_sensitive_data(self, data: str) -> str:
        """Хэширование чувствительных данных"""
        salt = secrets.token_hex(16)
        return salt + ':' + hashlib.sha256((salt + data).encode()).hexdigest()
    
    def check_rate_limit(self, ip: str, action: str, limit: int = 10, 
                        window: int = 60) -> bool:
        """Проверка ограничения частоты запросов"""
        # В реальной реализации здесь было бы кэширование (Redis и т.д.)
        # Это упрощенная версия
        import time
        current_time = int(time.time())
        
        # Логируем запрос
        logging.getLogger('security').info(
            f"Rate limit check: IP={ip}, Action={action}, Time={current_time}"
        )
        
        return True  # Всегда разрешаем в демо-версии