# web_app.py - Веб-приложение Flask
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_file
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_cors import CORS
from functools import wraps
import sqlite3
import json
import os
from database import Database
from auth import AuthManager
from config import Config

app = Flask(__name__)
app.secret_key = Config.SECRET_KEY

# Настройка безопасности
app.config.update(
    SESSION_COOKIE_SECURE=Config.REQUIRE_HTTPS,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=Config.SESSION_TIMEOUT.total_seconds()
)

# Настройка CORS
CORS(app, origins=Config.CORS_ORIGINS)

# Инициализация Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'web_login'
login_manager.login_message = "Пожалуйста, войдите в систему"

class User(UserMixin):
    def __init__(self, user_data):
        self.id = user_data['id']
        self.username = user_data['username']
        self.role = user_data['role']
        self.full_name = user_data['full_name']

@login_manager.user_loader
def load_user(user_id):
    db = Database()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT * FROM employees WHERE id = ? AND is_active = 1", (user_id,))
        user_data = cursor.fetchone()
        
        if user_data:
            return User(dict(user_data))
        return None
    finally:
        conn.close()

def get_db():
    """Получение подключения к БД"""
    return Database()

def role_required(role):
    """Декоратор для проверки роли"""
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            if current_user.role != role and current_user.role != 'admin':
                return jsonify({"error": "Доступ запрещен"}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.route('/')
def index():
    """Главная страница сайта"""
    db = get_db()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    try:
        # Получаем контент для главной страницы
        cursor.execute("""
            SELECT * FROM website_content 
            WHERE page_name = 'index' AND is_published = 1 
            ORDER BY section
        """)
        
        sections = {}
        for row in cursor.fetchall():
            row_dict = dict(row)
            sections[row_dict['section']] = {
                'content': row_dict['content'],
                'content_type': row_dict['content_type']
            }
        
        # Получаем товары для отображения
        cursor.execute("SELECT * FROM products WHERE is_active = 1 LIMIT 12")
        products = [dict(row) for row in cursor.fetchall()]
        
        return render_template('index.html', 
                             sections=sections, 
                             products=products,
                             company_name=Config.COMPANY_NAME)
    finally:
        conn.close()

@app.route('/login', methods=['GET', 'POST'])
def web_login():
    """Вход на сайт для сотрудников"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            return render_template('login.html', error="Заполните все поля")
        
        db = get_db()
        auth = AuthManager(db, Config.SECRET_KEY)
        
        user = auth.login(username, password, 
                         ip=request.remote_addr,
                         user_agent=request.user_agent.string)
        
        if user:
            user_obj = User(user)
            login_user(user_obj)
            
            # Логируем вход через веб
            db.log_audit(
                user['id'],
                'WEB_LOGIN_SUCCESS',
                'employees',
                user['id'],
                ip=request.remote_addr,
                user_agent=request.user_agent.string
            )
            
            return redirect(url_for('admin_panel'))
        
        return render_template('login.html', error="Неверный логин или пароль")
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def web_logout():
    """Выход из системы"""
    db = get_db()
    auth = AuthManager(db, Config.SECRET_KEY)
    
    # Логируем выход
    db.log_audit(
        current_user.id,
        'WEB_LOGOUT',
        'employees',
        current_user.id,
        ip=request.remote_addr,
        user_agent=request.user_agent.string
    )
    
    auth.logout(current_user.id)
    logout_user()
    return redirect(url_for('index'))

@app.route('/admin')
@login_required
@role_required('content_manager')
def admin_panel():
    """Панель управления контентом"""
    return render_template('admin_panel.html', 
                         user=current_user,
                         company_name=Config.COMPANY_NAME)

@app.route('/api/content', methods=['GET'])
def get_content():
    """API для получения контента"""
    page = request.args.get('page', 'index')
    
    db = get_db()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT * FROM website_content 
            WHERE page_name = ? AND is_published = 1
            ORDER BY section
        """, (page,))
        
        content = [dict(row) for row in cursor.fetchall()]
        return jsonify(content)
    finally:
        conn.close()

@app.route('/api/content', methods=['POST', 'PUT'])
@login_required
def manage_content():
    """API для управления контентом"""
    if current_user.role not in ['admin', 'content_manager']:
        return jsonify({"error": "Доступ запрещен"}), 403
    
    data = request.json
    
    if not data or 'page_name' not in data or 'section' not in data:
        return jsonify({"error": "Неверные данные"}), 400
    
    db = get_db()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    try:
        if request.method == 'POST':
            cursor.execute("""
                INSERT INTO website_content 
                (page_name, section, content_type, content, metadata, created_by)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                data['page_name'],
                data['section'],
                data.get('content_type', 'text'),
                data.get('content', ''),
                json.dumps(data.get('metadata', {})),
                current_user.id
            ))
        else:  # PUT
            cursor.execute("""
                UPDATE website_content 
                SET content = ?, 
                    content_type = ?,
                    metadata = ?, 
                    updated_at = CURRENT_TIMESTAMP,
                    version = version + 1
                WHERE page_name = ? AND section = ?
            """, (
                data.get('content', ''),
                data.get('content_type', 'text'),
                json.dumps(data.get('metadata', {})),
                data['page_name'],
                data['section']
            ))
        
        conn.commit()
        
        # Логируем изменение контента
        db.log_audit(
            current_user.id,
            f'CONTENT_{request.method}',
            'website_content',
            None,
            new_values=data,
            ip=request.remote_addr,
            user_agent=request.user_agent.string
        )
        
        return jsonify({"success": True})
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@app.route('/products')
def products_page():
    """Страница товаров"""
    category = request.args.get('category')
    
    db = get_db()
    products = db.get_products(category=category, limit=50)
    
    return render_template('products.html', 
                         products=products, 
                         category=category,
                         company_name=Config.COMPANY_NAME)

@app.route('/api/products')
def api_products():
    """API для получения товаров"""
    category = request.args.get('category')
    
    db = get_db()
    products = db.get_products(category=category, limit=100)
    
    return jsonify(products)

@app.route('/health')
def health_check():
    """Проверка работоспособности API"""
    return jsonify({"status": "ok", "service": "trade_enterprise"})

if __name__ == '__main__':
    print(f"Запуск веб-приложения на http://localhost:5000")
    
    # Создаем директорию для шаблонов, если её нет
    os.makedirs('templates', exist_ok=True)
    
    # Запускаем приложение
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,
        ssl_context='adhoc' if Config.REQUIRE_HTTPS else None
    )