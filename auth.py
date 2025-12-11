# auth.py - Модуль аутентификации и авторизации
import jwt
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from database import Database

class AuthManager:
    def __init__(self, db: Database, secret_key: str = None):
        self.db = db
        self.secret_key = secret_key or secrets.token_hex(32)
        self.session_timeout = timedelta(hours=8)
        self.max_failed_attempts = 5
    
    def login(self, username: str, password: str, 
              ip: str = None, user_agent: str = None) -> Optional[Dict[str, Any]]:
        """Вход в систему"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        try:
            # Проверяем количество неудачных попыток
            cursor.execute('''
                SELECT failed_login_attempts FROM employees 
                WHERE username = ? AND is_active = 1
            ''', (username,))
            
            result = cursor.fetchone()
            if result and result['failed_login_attempts'] >= self.max_failed_attempts:
                self.db.log_audit(
                    employee_id=None,
                    action='LOGIN_BLOCKED',
                    table_name='employees',
                    record_id=None,
                    ip=ip,
                    user_agent=user_agent
                )
                return None
            
            # Аутентифицируем пользователя
            user = self.db.authenticate_user(username, password)
            
            if user:
                # Создаем JWT токен
                token_payload = {
                    'user_id': user['id'],
                    'username': user['username'],
                    'role': user['role'],
                    'exp': datetime.utcnow() + self.session_timeout
                }
                
                token = jwt.encode(token_payload, self.secret_key, algorithm='HS256')
                
                # Обновляем информацию о пользователе
                cursor.execute('''
                    UPDATE employees 
                    SET last_login = CURRENT_TIMESTAMP,
                        failed_login_attempts = 0,
                        session_token = ?
                    WHERE id = ?
                ''', (token, user['id']))
                
                # Создаем запись сессии
                cursor.execute('''
                    INSERT INTO user_sessions 
                    (employee_id, session_token, ip_address, user_agent, expires_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    user['id'],
                    token,
                    ip,
                    user_agent,
                    (datetime.utcnow() + self.session_timeout).isoformat()
                ))
                
                conn.commit()
                
                # Логируем успешный вход
                self.db.log_audit(
                    employee_id=user['id'],
                    action='LOGIN_SUCCESS',
                    table_name='employees',
                    record_id=user['id'],
                    ip=ip,
                    user_agent=user_agent
                )
                
                user['token'] = token
                return user
            else:
                # Увеличиваем счетчик неудачных попыток
                cursor.execute('''
                    UPDATE employees 
                    SET failed_login_attempts = failed_login_attempts + 1
                    WHERE username = ?
                ''', (username,))
                
                conn.commit()
                
                # Логируем неудачную попытку входа
                self.db.log_audit(
                    employee_id=None,
                    action='LOGIN_FAILED',
                    table_name='employees',
                    record_id=None,
                    ip=ip,
                    user_agent=user_agent
                )
                
                return None
        except Exception as e:
            print(f"Ошибка при входе: {e}")
            return None
        finally:
            conn.close()
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Проверка JWT токена"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def logout(self, user_id: int, token: str = None):
        """Выход из системы"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        try:
            if token:
                cursor.execute('''
                    UPDATE user_sessions 
                    SET is_active = 0 
                    WHERE employee_id = ? AND session_token = ?
                ''', (user_id, token))
            else:
                cursor.execute('''
                    UPDATE user_sessions 
                    SET is_active = 0 
                    WHERE employee_id = ?
                ''', (user_id,))
            
            cursor.execute('''
                UPDATE employees 
                SET session_token = NULL 
                WHERE id = ?
            ''', (user_id,))
            
            conn.commit()
            
            # Логируем выход
            self.db.log_audit(
                employee_id=user_id,
                action='LOGOUT',
                table_name='employees',
                record_id=user_id
            )
        except Exception as e:
            print(f"Ошибка при выходе: {e}")
        finally:
            conn.close()
    
    def has_permission(self, user_role: str, required_role: str) -> bool:
        """Проверка прав доступа"""
        role_hierarchy = {
            'admin': 5,
            'manager': 4,
            'content_manager': 3,
            'cashier': 2,
            'viewer': 1
        }
        
        user_level = role_hierarchy.get(user_role, 0)
        required_level = role_hierarchy.get(required_role, 0)
        
        return user_level >= required_level
    
    def get_role_permissions(self, role: str) -> Dict[str, bool]:
        """Получение прав для роли"""
        permissions = {
            'view': True,
            'create': False,
            'edit': False,
            'delete': False,
            'manage_users': False,
            'manage_content': False,
            'view_audit': False
        }
        
        if role == 'admin':
            permissions.update({k: True for k in permissions})
        elif role == 'manager':
            permissions.update({
                'create': True,
                'edit': True,
                'delete': True,
                'manage_content': True
            })
        elif role == 'content_manager':
            permissions.update({
                'create': True,
                'edit': True,
                'manage_content': True
            })
        elif role == 'cashier':
            permissions.update({
                'create': True,
                'edit': True
            })
        
        return permissions