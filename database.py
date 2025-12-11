# database.py - Основной модуль базы данных
import sqlite3
import hashlib
import secrets
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path: str = "trade_enterprise.db"):
        self.db_path = db_path
        self.init_db()
        self.setup_logging()
    
    def setup_logging(self):
        """Настройка логирования"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('database.log'),
                logging.StreamHandler()
            ]
        )
    
    def get_connection(self) -> sqlite3.Connection:
        """Создание подключения к базе данных"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    
    def init_db(self):
        """Инициализация базы данных и создание таблиц"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Таблица сотрудников
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS employees (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    full_name TEXT NOT NULL,
                    email TEXT,
                    phone TEXT,
                    position TEXT,
                    role TEXT CHECK(role IN ('admin', 'manager', 'cashier', 'content_manager', 'viewer')) DEFAULT 'viewer',
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    password_changed_at TIMESTAMP,
                    failed_login_attempts INTEGER DEFAULT 0,
                    session_token TEXT,
                    must_change_password INTEGER DEFAULT 1
                )
            ''')
            
            # Таблица клиентов (соответствует ФЗ-152)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS clients (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_code TEXT UNIQUE NOT NULL,
                    full_name TEXT NOT NULL,
                    phone TEXT,
                    email TEXT,
                    address TEXT,
                    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    personal_data_consent INTEGER DEFAULT 0,
                    consent_date TIMESTAMP,
                    is_active INTEGER DEFAULT 1,
                    notes TEXT,
                    created_by INTEGER,
                    FOREIGN KEY (created_by) REFERENCES employees(id)
                )
            ''')
            
            # Таблица товаров
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sku TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    category TEXT,
                    unit_price REAL NOT NULL CHECK(unit_price >= 0),
                    quantity INTEGER DEFAULT 0 CHECK(quantity >= 0),
                    min_quantity INTEGER DEFAULT 10,
                    max_quantity INTEGER DEFAULT 100,
                    supplier TEXT,
                    barcode TEXT,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица заказов (ордеров)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_number TEXT UNIQUE NOT NULL,
                    client_id INTEGER,
                    employee_id INTEGER NOT NULL,
                    status TEXT CHECK(status IN ('pending', 'processing', 'completed', 'cancelled')) DEFAULT 'pending',
                    total_amount REAL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    notes TEXT,
                    FOREIGN KEY (client_id) REFERENCES clients(id),
                    FOREIGN KEY (employee_id) REFERENCES employees(id)
                )
            ''')
            
            # Таблица позиций заказа
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS order_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id INTEGER NOT NULL,
                    product_id INTEGER NOT NULL,
                    quantity INTEGER NOT NULL CHECK(quantity > 0),
                    unit_price REAL NOT NULL,
                    total_price REAL NOT NULL,
                    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
                    FOREIGN KEY (product_id) REFERENCES products(id)
                )
            ''')
            
            # Таблица контента для сайта
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS website_content (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    page_name TEXT NOT NULL,
                    section TEXT NOT NULL,
                    content_type TEXT CHECK(content_type IN ('text', 'html', 'json', 'image_path')) DEFAULT 'text',
                    content TEXT,
                    metadata TEXT,
                    is_published INTEGER DEFAULT 1,
                    created_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    version INTEGER DEFAULT 1,
                    FOREIGN KEY (created_by) REFERENCES employees(id)
                )
            ''')
            
            # Таблица логов действий (для аудита)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    employee_id INTEGER,
                    action TEXT NOT NULL,
                    table_name TEXT,
                    record_id INTEGER,
                    old_values TEXT,
                    new_values TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (employee_id) REFERENCES employees(id)
                )
            ''')
            
            # Таблица сессий
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    employee_id INTEGER NOT NULL,
                    session_token TEXT UNIQUE NOT NULL,
                    ip_address TEXT,
                    user_agent TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    is_active INTEGER DEFAULT 1,
                    FOREIGN KEY (employee_id) REFERENCES employees(id)
                )
            ''')
            
            # Создаем индексы для производительности
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_clients_phone ON clients(phone)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_clients_email ON clients(email)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_client ON orders(client_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_employee ON orders(employee_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_products_sku ON products(sku)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_products_category ON products(category)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_employees_username ON employees(username)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_employee ON audit_log(employee_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_log(created_at)')
            
            # Создаем администратора по умолчанию
            admin_exists = cursor.execute("SELECT 1 FROM employees WHERE username = 'admin'").fetchone()
            if not admin_exists:
                admin_password = self._hash_password("Admin123!")
                cursor.execute('''
                    INSERT INTO employees 
                    (username, password_hash, full_name, email, role, must_change_password) 
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', ('admin', admin_password, 'Администратор Системы', 'admin@example.com', 'admin', 1))
                logger.info("Создан администратор по умолчанию")
            
            conn.commit()
            logger.info("База данных успешно инициализирована")
            
        except Exception as e:
            logger.error(f"Ошибка при инициализации базы данных: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _hash_password(self, password: str) -> str:
        """Хэширование пароля с использованием соли"""
        salt = secrets.token_hex(16)
        return salt + ':' + hashlib.sha256((salt + password).encode()).hexdigest()
    
    def verify_password(self, stored_hash: str, password: str) -> bool:
        """Проверка пароля"""
        try:
            if not stored_hash or ':' not in stored_hash:
                return False
            salt, hash_value = stored_hash.split(':')
            return hash_value == hashlib.sha256((salt + password).encode()).hexdigest()
        except Exception as e:
            logger.error(f"Ошибка при проверке пароля: {e}")
            return False
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Аутентификация пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT * FROM employees 
                WHERE username = ? AND is_active = 1
            ''', (username,))
            
            user = cursor.fetchone()
            if user and self.verify_password(user['password_hash'], password):
                # Преобразуем строки в словарь
                user_dict = dict(user)
                return user_dict
            return None
        except Exception as e:
            logger.error(f"Ошибка аутентификации для пользователя {username}: {e}")
            return None
        finally:
            conn.close()
    
    def log_audit(self, employee_id: Optional[int], action: str, 
                 table_name: str = None, record_id: int = None, 
                 old_values: Any = None, new_values: Any = None, 
                 ip: str = None, user_agent: str = None):
        """Логирование действий для аудита"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO audit_log 
                (employee_id, action, table_name, record_id, old_values, new_values, ip_address, user_agent)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                employee_id, 
                action, 
                table_name, 
                record_id,
                json.dumps(old_values) if old_values else None,
                json.dumps(new_values) if new_values else None,
                ip, 
                user_agent
            ))
            
            conn.commit()
        except Exception as e:
            logger.error(f"Ошибка при записи в аудит-лог: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def get_clients(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Получение списка клиентов"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT * FROM clients 
                WHERE is_active = 1 
                ORDER BY id DESC 
                LIMIT ? OFFSET ?
            ''', (limit, offset))
            
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    def get_products(self, category: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Получение списка товаров"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            if category:
                cursor.execute('''
                    SELECT * FROM products 
                    WHERE is_active = 1 AND category = ?
                    ORDER BY name
                    LIMIT ?
                ''', (category, limit))
            else:
                cursor.execute('''
                    SELECT * FROM products 
                    WHERE is_active = 1
                    ORDER BY name
                    LIMIT ?
                ''', (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    def create_client(self, client_data: Dict[str, Any], employee_id: int) -> Optional[int]:
        """Создание нового клиента"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Генерация уникального кода клиента
            from datetime import datetime
            client_code = f"C{datetime.now().strftime('%Y%m%d')}{secrets.token_hex(4).upper()}"
            
            cursor.execute('''
                INSERT INTO clients 
                (client_code, full_name, phone, email, address, 
                 personal_data_consent, consent_date, notes, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                client_code,
                client_data.get('full_name'),
                client_data.get('phone'),
                client_data.get('email'),
                client_data.get('address'),
                1 if client_data.get('personal_data_consent') else 0,
                datetime.now().isoformat() if client_data.get('personal_data_consent') else None,
                client_data.get('notes'),
                employee_id
            ))
            
            client_id = cursor.lastrowid
            
            # Логируем действие
            self.log_audit(
                employee_id=employee_id,
                action='CREATE_CLIENT',
                table_name='clients',
                record_id=client_id,
                new_values=client_data
            )
            
            conn.commit()
            return client_id
        except sqlite3.IntegrityError as e:
            logger.error(f"Ошибка при создании клиента: {e}")
            return None
        except Exception as e:
            logger.error(f"Ошибка при создании клиента: {e}")
            conn.rollback()
            return None
        finally:
            conn.close()
    
    def create_order(self, order_data: Dict[str, Any], employee_id: int) -> Optional[int]:
        """Создание нового заказа"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            conn.execute("BEGIN TRANSACTION")
            
            # Генерация номера заказа
            from datetime import datetime
            order_number = f"ORD{datetime.now().strftime('%Y%m%d%H%M%S')}{secrets.token_hex(2).upper()}"
            
            # Создаем заказ
            cursor.execute('''
                INSERT INTO orders 
                (order_number, client_id, employee_id, status, notes)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                order_number,
                order_data.get('client_id'),
                employee_id,
                'pending',
                order_data.get('notes')
            ))
            
            order_id = cursor.lastrowid
            total_amount = 0
            
            # Добавляем товары в заказ
            for item in order_data.get('items', []):
                product_id = item.get('product_id')
                quantity = item.get('quantity')
                
                # Получаем цену товара
                cursor.execute('SELECT unit_price, quantity FROM products WHERE id = ?', (product_id,))
                product = cursor.fetchone()
                
                if not product:
                    raise ValueError(f"Товар с ID {product_id} не найден")
                
                if product['quantity'] < quantity:
                    raise ValueError(f"Недостаточно товара в наличии. Доступно: {product['quantity']}")
                
                unit_price = product['unit_price']
                item_total = unit_price * quantity
                total_amount += item_total
                
                # Добавляем позицию в заказ
                cursor.execute('''
                    INSERT INTO order_items 
                    (order_id, product_id, quantity, unit_price, total_price)
                    VALUES (?, ?, ?, ?, ?)
                ''', (order_id, product_id, quantity, unit_price, item_total))
                
                # Обновляем количество товара
                cursor.execute('''
                    UPDATE products 
                    SET quantity = quantity - ?, 
                        last_updated = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (quantity, product_id))
            
            # Обновляем общую сумму заказа
            cursor.execute('''
                UPDATE orders 
                SET total_amount = ?
                WHERE id = ?
            ''', (total_amount, order_id))
            
            # Логируем действие
            self.log_audit(
                employee_id=employee_id,
                action='CREATE_ORDER',
                table_name='orders',
                record_id=order_id,
                new_values=order_data
            )
            
            conn.commit()
            return order_id
        except Exception as e:
            logger.error(f"Ошибка при создании заказа: {e}")
            conn.rollback()
            return None
        finally:
            conn.close()
    
    def update_password(self, employee_id: int, new_password: str) -> bool:
        """Обновление пароля пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            password_hash = self._hash_password(new_password)
            
            cursor.execute('''
                UPDATE employees 
                SET password_hash = ?, 
                    password_changed_at = CURRENT_TIMESTAMP,
                    must_change_password = 0
                WHERE id = ?
            ''', (password_hash, employee_id))
            
            if cursor.rowcount > 0:
                # Логируем смену пароля
                self.log_audit(
                    employee_id=employee_id,
                    action='PASSWORD_CHANGE',
                    table_name='employees',
                    record_id=employee_id
                )
                
                conn.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Ошибка при обновлении пароля: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()