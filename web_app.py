# web_app.py - Веб-приложение Flask
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_cors import CORS
from functools import wraps
import sqlite3
import json
import os
import secrets
from datetime import datetime
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
    PERMANENT_SESSION_LIFETIME=Config.SESSION_TIMEOUT.total_seconds(),
    TEMPLATES_AUTO_RELOAD=True
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
                return render_template('error.html', 
                                     error="Доступ запрещен", 
                                     message="У вас недостаточно прав для доступа к этой странице"), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.context_processor
def inject_globals():
    """Добавляет глобальные переменные во все шаблоны"""
    return {
        'current_year': datetime.now().year,
        'company_name': Config.COMPANY_NAME,
        'current_user': current_user
    }

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
        cursor.execute("SELECT * FROM products WHERE is_active = 1 LIMIT 8")
        products = [dict(row) for row in cursor.fetchall()]
        
        # Получаем статистику для отображения
        cursor.execute("SELECT COUNT(*) as count FROM products WHERE is_active = 1")
        products_count = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM clients WHERE is_active = 1")
        clients_count = cursor.fetchone()['count']
        
        cursor.execute("""
            SELECT COUNT(*) as count FROM orders 
            WHERE status = 'completed' 
            AND DATE(created_at) = DATE('now')
        """)
        today_orders = cursor.fetchone()['count']
        
        return render_template('index.html', 
                             sections=sections, 
                             products=products,
                             products_count=products_count,
                             clients_count=clients_count,
                             today_orders=today_orders)
    except Exception as e:
        app.logger.error(f"Ошибка на главной странице: {e}")
        return render_template('error.html', 
                             error="Ошибка загрузки страницы",
                             message="Произошла ошибка при загрузке данных")
    finally:
        conn.close()

@app.route('/login', methods=['GET', 'POST'])
def web_login():
    """Вход на сайт для сотрудников"""
    if current_user.is_authenticated:
        return redirect(url_for('admin_panel'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash("Заполните все поля", "error")
            return render_template('login.html')
        
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
            
            flash(f"Добро пожаловать, {user['full_name']}!", "success")
            return redirect(url_for('admin_panel'))
        
        flash("Неверный логин или пароль", "error")
    
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
    flash("Вы успешно вышли из системы", "success")
    return redirect(url_for('index'))

@app.route('/admin')
@login_required
@role_required('content_manager')
def admin_panel():
    """Панель управления контентом"""
    db = get_db()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    try:
        # Получаем статистику для панели управления
        cursor.execute("SELECT COUNT(*) as count FROM products WHERE is_active = 1")
        products_count = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM clients WHERE is_active = 1")
        clients_count = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM orders")
        orders_count = cursor.fetchone()['count']
        
        cursor.execute("""
            SELECT COUNT(*) as count FROM orders 
            WHERE status = 'completed' 
            AND DATE(created_at) = DATE('now')
        """)
        today_orders = cursor.fetchone()['count']
        
        # Получаем последние заказы
        cursor.execute("""
            SELECT o.*, c.full_name as client_name 
            FROM orders o
            LEFT JOIN clients c ON o.client_id = c.id
            ORDER BY o.created_at DESC 
            LIMIT 5
        """)
        recent_orders = [dict(row) for row in cursor.fetchall()]
        
        # Получаем товары с низким запасом
        cursor.execute("""
            SELECT * FROM products 
            WHERE is_active = 1 AND quantity < min_quantity
            ORDER BY quantity ASC 
            LIMIT 5
        """)
        low_stock = [dict(row) for row in cursor.fetchall()]
        
        return render_template('admin_panel.html',
                             products_count=products_count,
                             clients_count=clients_count,
                             orders_count=orders_count,
                             today_orders=today_orders,
                             recent_orders=recent_orders,
                             low_stock=low_stock)
    except Exception as e:
        app.logger.error(f"Ошибка в панели управления: {e}")
        return render_template('error.html',
                             error="Ошибка загрузки панели управления",
                             message="Произошла ошибка при загрузке данных")
    finally:
        conn.close()

@app.route('/admin/content')
@login_required
@role_required('content_manager')
def content_management():
    """Управление контентом сайта"""
    db = get_db()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    try:
        # Получаем все страницы контента
        cursor.execute("""
            SELECT page_name, section, content_type, content, is_published, 
                   created_at, updated_at, created_by
            FROM website_content 
            ORDER BY page_name, section
        """)
        
        content_items = [dict(row) for row in cursor.fetchall()]
        
        # Группируем по страницам
        pages = {}
        for item in content_items:
            page = item['page_name']
            if page not in pages:
                pages[page] = []
            pages[page].append(item)
        
        return render_template('content_management.html', pages=pages)
    except Exception as e:
        app.logger.error(f"Ошибка управления контентом: {e}")
        return render_template('error.html',
                             error="Ошибка загрузки контента",
                             message="Произошла ошибка при загрузке данных")
    finally:
        conn.close()

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
    except Exception as e:
        app.logger.error(f"Ошибка получения контента: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@app.route('/api/content', methods=['POST', 'PUT', 'DELETE'])
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
            # Проверяем существование
            cursor.execute("""
                SELECT id FROM website_content 
                WHERE page_name = ? AND section = ?
            """, (data['page_name'], data['section']))
            
            if cursor.fetchone():
                return jsonify({"error": "Раздел уже существует"}), 400
            
            cursor.execute("""
                INSERT INTO website_content 
                (page_name, section, content_type, content, metadata, created_by, is_published)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                data['page_name'],
                data['section'],
                data.get('content_type', 'text'),
                data.get('content', ''),
                json.dumps(data.get('metadata', {})),
                current_user.id,
                data.get('is_published', True)
            ))
            
            action = 'CREATE_CONTENT'
            
        elif request.method == 'PUT':
            cursor.execute("""
                UPDATE website_content 
                SET content = ?, 
                    content_type = ?,
                    metadata = ?, 
                    updated_at = CURRENT_TIMESTAMP,
                    is_published = ?,
                    version = version + 1
                WHERE page_name = ? AND section = ?
            """, (
                data.get('content', ''),
                data.get('content_type', 'text'),
                json.dumps(data.get('metadata', {})),
                data.get('is_published', True),
                data['page_name'],
                data['section']
            ))
            
            if cursor.rowcount == 0:
                return jsonify({"error": "Раздел не найден"}), 404
            
            action = 'UPDATE_CONTENT'
            
        elif request.method == 'DELETE':
            cursor.execute("""
                DELETE FROM website_content 
                WHERE page_name = ? AND section = ?
            """, (data['page_name'], data['section']))
            
            if cursor.rowcount == 0:
                return jsonify({"error": "Раздел не найден"}), 404
            
            action = 'DELETE_CONTENT'
        
        conn.commit()
        
        # Логируем действие
        db.log_audit(
            current_user.id,
            action,
            'website_content',
            None,
            new_values=data,
            ip=request.remote_addr,
            user_agent=request.user_agent.string
        )
        
        return jsonify({"success": True})
        
    except Exception as e:
        conn.rollback()
        app.logger.error(f"Ошибка управления контентом: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@app.route('/products')
def products_page():
    """Страница товаров"""
    category = request.args.get('category')
    search = request.args.get('search', '')
    page = int(request.args.get('page', 1))
    per_page = 12
    
    db = get_db()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    try:
        # Получаем категории
        cursor.execute("""
            SELECT DISTINCT category FROM products 
            WHERE is_active = 1 AND category IS NOT NULL 
            ORDER BY category
        """)
        categories = [row['category'] for row in cursor.fetchall()]
        
        # Строим запрос в зависимости от параметров
        query = """
            SELECT * FROM products 
            WHERE is_active = 1
        """
        params = []
        
        if category and category != 'Все':
            query += " AND category = ?"
            params.append(category)
        
        if search:
            query += " AND (name LIKE ? OR sku LIKE ? OR description LIKE ?)"
            search_term = f"%{search}%"
            params.extend([search_term, search_term, search_term])
        
        query += " ORDER BY name"
        
        # Получаем товары
        cursor.execute(query, params)
        all_products = [dict(row) for row in cursor.fetchall()]
        
        # Пагинация
        total = len(all_products)
        start = (page - 1) * per_page
        end = start + per_page
        products = all_products[start:end]
        total_pages = (total + per_page - 1) // per_page
        
        return render_template('products.html', 
                             products=products,
                             categories=categories,
                             selected_category=category,
                             search=search,
                             page=page,
                             total_pages=total_pages,
                             total=total)
    except Exception as e:
        app.logger.error(f"Ошибка страницы товаров: {e}")
        return render_template('error.html',
                             error="Ошибка загрузки товаров",
                             message="Произошла ошибка при загрузке данных")
    finally:
        conn.close()

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    """Страница товара"""
    db = get_db()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT * FROM products 
            WHERE id = ? AND is_active = 1
        """, (product_id,))
        
        product = cursor.fetchone()
        
        if not product:
            return render_template('error.html',
                                 error="Товар не найден",
                                 message="Запрошенный товар не существует или был удален"), 404
        
        # Получаем похожие товары
        cursor.execute("""
            SELECT * FROM products 
            WHERE is_active = 1 AND category = ? AND id != ?
            ORDER BY RANDOM() 
            LIMIT 4
        """, (product['category'], product_id))
        
        similar_products = [dict(row) for row in cursor.fetchall()]
        
        return render_template('product_detail.html',
                             product=dict(product),
                             similar_products=similar_products)
    except Exception as e:
        app.logger.error(f"Ошибка детальной страницы товара: {e}")
        return render_template('error.html',
                             error="Ошибка загрузки товара",
                             message="Произошла ошибка при загрузке данных")
    finally:
        conn.close()

@app.route('/api/products')
def api_products():
    """API для получения товаров"""
    category = request.args.get('category')
    limit = int(request.args.get('limit', 50))
    
    db = get_db()
    products = db.get_products(category=category, limit=limit)
    
    return jsonify(products)

@app.route('/about')
def about_page():
    """Страница "О компании" """
    db = get_db()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT * FROM website_content 
            WHERE page_name = 'about' AND is_published = 1
            ORDER BY section
        """)
        
        sections = {}
        for row in cursor.fetchall():
            row_dict = dict(row)
            sections[row_dict['section']] = {
                'content': row_dict['content'],
                'content_type': row_dict['content_type']
            }
        
        return render_template('about.html', sections=sections)
    except Exception as e:
        app.logger.error(f"Ошибка страницы 'О компании': {e}")
        return render_template('error.html',
                             error="Ошибка загрузки страницы",
                             message="Произошла ошибка при загрузке данных")
    finally:
        conn.close()

@app.route('/contacts')
def contacts_page():
    """Страница контактов"""
    db = get_db()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT * FROM website_content 
            WHERE page_name = 'contacts' AND is_published = 1
            ORDER BY section
        """)
        
        sections = {}
        for row in cursor.fetchall():
            row_dict = dict(row)
            sections[row_dict['section']] = {
                'content': row_dict['content'],
                'content_type': row_dict['content_type']
            }
        
        return render_template('contacts.html', sections=sections)
    except Exception as e:
        app.logger.error(f"Ошибка страницы контактов: {e}")
        return render_template('error.html',
                             error="Ошибка загрузки страницы",
                             message="Произошла ошибка при загрузке данных")
    finally:
        conn.close()

@app.route('/admin/users')
@login_required
@role_required('admin')
def users_management():
    """Управление пользователями (только для админов)"""
    db = get_db()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT * FROM employees ORDER BY role, username")
        users = [dict(row) for row in cursor.fetchall()]
        
        return render_template('users_management.html', users=users)
    except Exception as e:
        app.logger.error(f"Ошибка управления пользователями: {e}")
        return render_template('error.html',
                             error="Ошибка загрузки пользователей",
                             message="Произошла ошибка при загрузке данных")
    finally:
        conn.close()

@app.route('/admin/orders')
@login_required
@role_required('manager')
def orders_management():
    """Управление заказами (для менеджеров и админов)"""
    status = request.args.get('status', 'Все')
    
    db = get_db()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    try:
        if status != 'Все':
            cursor.execute("""
                SELECT o.*, c.full_name as client_name, e.full_name as employee_name
                FROM orders o
                LEFT JOIN clients c ON o.client_id = c.id
                LEFT JOIN employees e ON o.employee_id = e.id
                WHERE o.status = ?
                ORDER BY o.created_at DESC
            """, (status,))
        else:
            cursor.execute("""
                SELECT o.*, c.full_name as client_name, e.full_name as employee_name
                FROM orders o
                LEFT JOIN clients c ON o.client_id = c.id
                LEFT JOIN employees e ON o.employee_id = e.id
                ORDER BY o.created_at DESC
            """)
        
        orders = [dict(row) for row in cursor.fetchall()]
        
        # Статистика по заказам
        cursor.execute("SELECT COUNT(*) as total FROM orders")
        total_orders = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) as count FROM orders WHERE status = 'pending'")
        pending_orders = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM orders WHERE status = 'processing'")
        processing_orders = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM orders WHERE status = 'completed'")
        completed_orders = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM orders WHERE status = 'cancelled'")
        cancelled_orders = cursor.fetchone()['count']
        
        return render_template('orders_management.html',
                             orders=orders,
                             status=status,
                             total_orders=total_orders,
                             pending_orders=pending_orders,
                             processing_orders=processing_orders,
                             completed_orders=completed_orders,
                             cancelled_orders=cancelled_orders)
    except Exception as e:
        app.logger.error(f"Ошибка управления заказами: {e}")
        return render_template('error.html',
                             error="Ошибка загрузки заказов",
                             message="Произошла ошибка при загрузке данных")
    finally:
        conn.close()

@app.route('/profile')
@login_required
def user_profile():
    """Профиль пользователя"""
    db = get_db()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT * FROM employees WHERE id = ?
        """, (current_user.id,))
        
        user = cursor.fetchone()
        
        # Получаем статистику пользователя
        cursor.execute("""
            SELECT COUNT(*) as count FROM orders 
            WHERE employee_id = ?
        """, (current_user.id,))
        
        user_orders = cursor.fetchone()['count']
        
        cursor.execute("""
            SELECT COUNT(*) as count FROM orders 
            WHERE employee_id = ? AND status = 'completed'
        """, (current_user.id,))
        
        completed_orders = cursor.fetchone()['count']
        
        # Получаем последние действия пользователя
        cursor.execute("""
            SELECT * FROM audit_log 
            WHERE employee_id = ? 
            ORDER BY created_at DESC 
            LIMIT 10
        """, (current_user.id,))
        
        recent_actions = [dict(row) for row in cursor.fetchall()]
        
        return render_template('profile.html',
                             user=dict(user),
                             user_orders=user_orders,
                             completed_orders=completed_orders,
                             recent_actions=recent_actions)
    except Exception as e:
        app.logger.error(f"Ошибка профиля пользователя: {e}")
        return render_template('error.html',
                             error="Ошибка загрузки профиля",
                             message="Произошла ошибка при загрузке данных")
    finally:
        conn.close()

@app.route('/api/order/<int:order_id>')
@login_required
def api_order_details(order_id):
    """API для получения деталей заказа"""
    db = get_db()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    try:
        # Проверяем права доступа
        if current_user.role not in ['admin', 'manager']:
            cursor.execute("SELECT employee_id FROM orders WHERE id = ?", (order_id,))
            order = cursor.fetchone()
            if not order or order['employee_id'] != current_user.id:
                return jsonify({"error": "Доступ запрещен"}), 403
        
        # Получаем информацию о заказе
        cursor.execute("""
            SELECT o.*, c.full_name as client_name, c.phone, c.email,
                   e.full_name as employee_name
            FROM orders o
            LEFT JOIN clients c ON o.client_id = c.id
            LEFT JOIN employees e ON o.employee_id = e.id
            WHERE o.id = ?
        """, (order_id,))
        
        order = cursor.fetchone()
        
        if not order:
            return jsonify({"error": "Заказ не найден"}), 404
        
        # Получаем товары в заказе
        cursor.execute("""
            SELECT oi.*, p.name, p.sku, p.category
            FROM order_items oi
            JOIN products p ON oi.product_id = p.id
            WHERE oi.order_id = ?
        """, (order_id,))
        
        items = [dict(row) for row in cursor.fetchall()]
        
        return jsonify({
            'order': dict(order),
            'items': items
        })
    except Exception as e:
        app.logger.error(f"Ошибка получения деталей заказа: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@app.route('/api/order/<int:order_id>/status', methods=['POST'])
@login_required
def api_update_order_status(order_id):
    """API для обновления статуса заказа"""
    if current_user.role not in ['admin', 'manager', 'cashier']:
        return jsonify({"error": "Доступ запрещен"}), 403
    
    data = request.json
    new_status = data.get('status')
    
    if not new_status or new_status not in ['pending', 'processing', 'completed', 'cancelled']:
        return jsonify({"error": "Неверный статус"}), 400
    
    db = get_db()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    try:
        # Получаем текущий статус
        cursor.execute("SELECT status FROM orders WHERE id = ?", (order_id,))
        order = cursor.fetchone()
        
        if not order:
            return jsonify({"error": "Заказ не найден"}), 404
        
        # Обновляем статус
        cursor.execute("""
            UPDATE orders 
            SET status = ?,
                completed_at = CASE WHEN ? = 'completed' THEN CURRENT_TIMESTAMP ELSE completed_at END
            WHERE id = ?
        """, (new_status, new_status, order_id))
        
        conn.commit()
        
        # Логируем действие
        db.log_audit(
            current_user.id,
            'UPDATE_ORDER_STATUS',
            'orders',
            order_id,
            old_values={'status': order['status']},
            new_values={'status': new_status},
            ip=request.remote_addr,
            user_agent=request.user_agent.string
        )
        
        # Если отмена заказа, возвращаем товары на склад
        if new_status == 'cancelled' and order['status'] != 'cancelled':
            cursor.execute("SELECT product_id, quantity FROM order_items WHERE order_id = ?", (order_id,))
            items = cursor.fetchall()
            
            for item in items:
                cursor.execute("""
                    UPDATE products 
                    SET quantity = quantity + ?, 
                        last_updated = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (item['quantity'], item['product_id']))
            
            conn.commit()
        
        return jsonify({"success": True})
    except Exception as e:
        conn.rollback()
        app.logger.error(f"Ошибка обновления статуса заказа: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@app.route('/api/stats')
def api_stats():
    """API для получения статистики"""
    db = get_db()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    try:
        # Общая статистика
        cursor.execute("SELECT COUNT(*) as count FROM products WHERE is_active = 1")
        products_count = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM clients WHERE is_active = 1")
        clients_count = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM orders")
        orders_count = cursor.fetchone()['count']
        
        # Статистика продаж за сегодня
        cursor.execute("""
            SELECT 
                COUNT(*) as today_orders,
                COALESCE(SUM(total_amount), 0) as today_revenue
            FROM orders 
            WHERE DATE(created_at) = DATE('now') 
                AND status = 'completed'
        """)
        today_stats = cursor.fetchone()
        
        # Статистика по месяцам
        cursor.execute("""
            SELECT 
                strftime('%Y-%m', created_at) as month,
                COUNT(*) as order_count,
                COALESCE(SUM(total_amount), 0) as revenue
            FROM orders 
            WHERE status = 'completed'
                AND created_at >= date('now', '-6 months')
            GROUP BY strftime('%Y-%m', created_at)
            ORDER BY month DESC
        """)
        monthly_stats = [dict(row) for row in cursor.fetchall()]
        
        # Топ товаров
        cursor.execute("""
            SELECT 
                p.name,
                p.sku,
                SUM(oi.quantity) as total_sold,
                SUM(oi.total_price) as total_revenue
            FROM order_items oi
            JOIN products p ON oi.product_id = p.id
            JOIN orders o ON oi.order_id = o.id
            WHERE o.status = 'completed'
                AND o.created_at >= date('now', '-30 days')
            GROUP BY p.id
            ORDER BY total_revenue DESC
            LIMIT 5
        """)
        top_products = [dict(row) for row in cursor.fetchall()]
        
        return jsonify({
            'products_count': products_count,
            'clients_count': clients_count,
            'orders_count': orders_count,
            'today_orders': today_stats['today_orders'],
            'today_revenue': today_stats['today_revenue'],
            'monthly_stats': monthly_stats,
            'top_products': top_products
        })
    except Exception as e:
        app.logger.error(f"Ошибка получения статистики: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@app.route('/health')
def health_check():
    """Проверка работоспособности API"""
    try:
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        conn.close()
        
        return jsonify({
            "status": "ok",
            "service": "trade_enterprise_web",
            "timestamp": datetime.now().isoformat(),
            "database": "connected"
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "service": "trade_enterprise_web",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }), 500

@app.errorhandler(404)
def page_not_found(e):
    """Обработчик 404 ошибок"""
    return render_template('error.html',
                         error="Страница не найдена",
                         message="Запрошенная страница не существует"), 404

@app.errorhandler(500)
def internal_server_error(e):
    """Обработчик 500 ошибок"""
    app.logger.error(f"Internal server error: {e}")
    return render_template('error.html',
                         error="Внутренняя ошибка сервера",
                         message="Произошла ошибка при обработке запроса"), 500

def init_website_content():
    """Инициализация контента сайта по умолчанию"""
    db = get_db()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    try:
        # Проверяем, есть ли уже контент
        cursor.execute("SELECT COUNT(*) as count FROM website_content")
        count = cursor.fetchone()['count']
        
        if count == 0:
            print("Инициализация контента сайта...")
            
            default_content = [
                # Главная страница
                ('index', 'hero', 'text', 
                 '<h1>Добро пожаловать в наш магазин!</h1><p>Мы предлагаем качественные товары по доступным ценам.</p>',
                 '{"order": 1}', 1),
                
                ('index', 'about', 'text',
                 '<h2>О нашей компании</h2><p>Мы работаем на рынке более 10 лет и заслужили доверие тысяч клиентов.</p>',
                 '{"order": 2}', 1),
                
                ('index', 'features', 'text',
                 '<h2>Наши преимущества</h2><ul><li>Качественные товары</li><li>Быстрая доставка</li><li>Гарантия качества</li></ul>',
                 '{"order": 3}', 1),
                
                # Страница "О компании"
                ('about', 'main', 'text',
                 '<h1>О компании</h1><p>Наша компания была основана в 2010 году и с тех пор успешно развивается на рынке.</p>',
                 '{"order": 1}', 1),
                
                ('about', 'history', 'text',
                 '<h2>История компании</h2><p>Начиная с небольшого магазина, мы выросли в крупную сеть с филиалами по всей стране.</p>',
                 '{"order": 2}', 1),
                
                ('about', 'team', 'text',
                 '<h2>Наша команда</h2><p>У нас работают профессионалы с многолетним опытом в своей области.</p>',
                 '{"order": 3}', 1),
                
                # Страница контактов
                ('contacts', 'main', 'text',
                 '<h1>Контакты</h1><p>Свяжитесь с нами любым удобным способом.</p>',
                 '{"order": 1}', 1),
                
                ('contacts', 'address', 'text',
                 '<h2>Адрес</h2><p>г. Москва, ул. Примерная, д. 123</p>',
                 '{"order": 2}', 1),
                
                ('contacts', 'phone', 'text',
                 '<h2>Телефон</h2><p>+7 (495) 123-45-67</p>',
                 '{"order": 3}', 1),
                
                ('contacts', 'email', 'text',
                 '<h2>Email</h2><p>info@example.com</p>',
                 '{"order": 4}', 1),
                
                ('contacts', 'schedule', 'text',
                 '<h2>Режим работы</h2><p>Пн-Пт: 9:00-18:00<br>Сб-Вс: 10:00-16:00</p>',
                 '{"order": 5}', 1),
            ]
            
            for content in default_content:
                cursor.execute("""
                    INSERT INTO website_content 
                    (page_name, section, content_type, content, metadata, is_published)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, content)
            
            conn.commit()
            print("Контент сайта инициализирован")
    except Exception as e:
        print(f"Ошибка инициализации контента: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    print(f"Запуск веб-приложения на http://localhost:5000")
    
    # Создаем директорию для шаблонов, если её нет
    os.makedirs('templates', exist_ok=True)
    
    # Инициализируем контент сайта
    init_website_content()
    
    # Запускаем приложение
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,
        ssl_context='adhoc' if Config.REQUIRE_HTTPS else None
    )