from flask import Flask, request, session, render_template_string, jsonify
import hashlib
import time
import sqlite3
import secrets
from threading import Lock
from collections import defaultdict, deque
import os
import bcrypt
import random

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
.
DB_PATH = "auth_system.sqlite3"

IP_WINDOW_SECONDS = 60
IP_MAX_REQUESTS = 30
IP_FAIL_LIMIT = 5
IP_BLOCK_SECONDS = 600

USER_FAIL_LIMIT = 3
USER_BLOCK_SECONDS = 300

GLOBAL_FAIL_LIMIT = 50
GLOBAL_BLOCK_SECONDS = 600

MIN_RESPONSE_TIME = 0.5
MAX_RESPONSE_JITTER = 0.3

_ip_lock = Lock()
_ip_requests = defaultdict(deque)
_ip_failures = defaultdict(int)
_ip_blocks = {}.

_user_lock = Lock()
_user_failures = {}
_user_blocks = {}

_global_lock = Lock()
_global_failure_count = 0
_global_block_until = 0

def init_db(): conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at INTEGER NOT NULL
        )
    """
    )

    cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'")
    if cursor.fetchone()[0] == 0:
        password_hash = bcrypt.hashpw(b"password", bcrypt.gensalt())
        cursor.execute(
            "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
            ("admin", password_hash, int(time.time()))
        )

    conn.commit()
    conn.close()

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_user(username):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()
    return user

def check_ip_rate_limit(ip):
    now = time.time()
    
    if ip in _ip_blocks and now < _ip_blocks[ip]:
        remaining = int(_ip_blocks[ip] - now)
        return False, f"IP временно заблокирован. Осталось: {remaining} секунд"
    
    with _ip_lock:
        requests = _ip_requests[ip]
        requests.append(now)
        
        while requests and requests[0] < now - IP_WINDOW_SECONDS:
            requests.popleft()
        
        if len(requests) > IP_MAX_REQUESTS:
            return False, "Слишком много запросов"
    
    return True, ""

def check_user_block(username):
    if not username:
        return True, ""
    
    now = time.time()
    
    with _user_lock:
        if username in _user_blocks and now < _user_blocks[username]:
            remaining = int(_user_blocks[username] - now)
            return False, f"аккаунт заблокирован. Осталось: {remaining} секунд"
    
    return True, ""

def check_global_block():
    now = time.time()
    
    with _global_lock:
        if now < _global_block_until:
            return False, "недоступен"
    
    return True, ""

def record_failure(username, ip):
    now = time.time()
    
    with _ip_lock:
        _ip_failures[ip] += 1
        if _ip_failures[ip] >= IP_FAIL_LIMIT:
            _ip_blocks[ip] = now + IP_BLOCK_SECONDS
    
    if username:
        with _user_lock:
            _user_failures[username] = _user_failures.get(username, 0) + 1
            if _user_failures[username] >= USER_FAIL_LIMIT:
                _user_blocks[username] = now + USER_BLOCK_SECONDS

def record_success(username, ip):
    with _ip_lock:
        _ip_failures[ip] = 0
        if ip in _ip_blocks:
            del _ip_blocks[ip]
    
    if username:
        with _user_lock:
            if username in _user_failures:
                del _user_failures[username]
            if username in _user_blocks:
                del _user_blocks[username]

def secure_verify_password(username, password):
    start_time = time.time()
    
    try:
        user = get_user(username)
        if not user:
            dummy_salt = bcrypt.gensalt()
            bcrypt.checkpw(b"dummy", dummy_salt)
            return False, None
        
        if bcrypt.checkpw(password.encode('utf-8'), user['password_hash']):
            return True, dict(user)
        else:
            return False, None
    except Exception:
        dummy_salt = bcrypt.gensalt()
        bcrypt.checkpw(b"dummy", dummy_salt)
        return False, None
    finally:
        elapsed = time.time() - start_time
        min_time = MIN_RESPONSE_TIME + random.uniform(0, MAX_RESPONSE_JITTER)
        if elapsed < min_time:
            time.sleep(min_time - elapsed)

def generate_csrf_token():
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_hex(32)
    return session['csrf_token']

LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Secure Auth System</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 400px; margin: 100px auto; padding: 20px; }
        .form-group { margin-bottom: 15px; }
        input[type="text"], input[type="password"] { 
            width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; 
        }
        input[type="submit"] { 
            background: #007bff; color: white; padding: 10px 20px; border: none; 
            border-radius: 4px; cursor: pointer; width: 100%;
        }
        input[type="submit"]:hover { background: #0056b3; }
        .error { color: #dc3545; background: #f8d7da; padding: 10px; 
                 border-radius: 4px; margin: 10px 0; }
        .success { color: #155724; background: #d4edda; padding: 10px; 
                   border-radius: 4px; margin: 10px 0; }
        .info { color: #0c5460; background: #d1ecf1; padding: 10px; 
                border-radius: 4px; margin: 10px 0; }
    </style>
</head>
<body>
    <h2>Secure Authentication</h2>
    
    <form method="GET" action="/vulnerabilities/brute/">
        <div class="form-group">
            <input type="text" name="username" value="{{ username }}" 
                   placeholder="Username" required>
        </div>
        <div class="form-group">
            <input type="password" name="password" placeholder="Password" required>
        </div>
        <input type="hidden" name="user_token" value="{{ token }}">
        <input type="submit" name="Login" value="Login">
    </form>
    
    {% if message and message_type == 'error' %}
    <div class="error">{{ message }}</div>
    {% endif %}
    
    {% if message and message_type == 'success' %}
    <div class="success">{{ message }}</div>
    {% endif %}
    
    {% if message and message_type == 'info' %}
    <div class="info">{{ message }}</div>
    {% endif %}
    
    <div style="margin-top: 20px; font-size: 0.9em; color: #666;">
    </div>
</body>
</html>
"""

@app.route("/")
def home():
    return """
    <h2>Secure Authentication System</h2>
    <p><a href="/vulnerabilities/brute/">Перейти к форме входа</a></p>
    """

@app.route("/vulnerabilities/brute/", methods=["GET"])
def brute_force_protected():
    username = request.args.get("username", "").strip()
    password = request.args.get("password", "")
    user_token = request.args.get("user_token", "")
    login_action = request.args.get("Login", "")
    client_ip = request.remote_addr or "unknown"
    
    csrf_token = generate_csrf_token()
    
    if not login_action:
        return render_template_string(
            LOGIN_TEMPLATE,
            username=username,
            token=csrf_token,
            message="",
            message_type=""
        )
    
    if user_token != csrf_token:
        session['csrf_token'] = secrets.token_hex(32)
        return render_template_string(
            LOGIN_TEMPLATE,
            username=username,
            token=session['csrf_token'],
            message="Неверный токен безопасности. Попробуйте снова.",
            message_type="error"
        )
    
    checks = [
        check_global_block(),
        check_ip_rate_limit(client_ip),
        check_user_block(username)
    ]
    
    for success, message in checks:
        if not success:
            session['csrf_token'] = secrets.token_hex(32)
            return render_template_string(
                LOGIN_TEMPLATE,
                username=username,
                token=session['csrf_token'],
                message=message,
                message_type="error"
            )
    
    if username and password:
        success, user = secure_verify_password(username, password)
        
        if success and user:
            record_success(username, client_ip)
            
            session['csrf_token'] = secrets.token_hex(32)
            
            safe_username = username.replace('<', '&lt;').replace('>', '&gt;')
            
            return render_template_string(
                LOGIN_TEMPLATE,
                username="",
                token=session['csrf_token'],
                message=f"Вход выполнен успешно",
                message_type="success"
            )
        else:
            record_failure(username, client_ip)
            session['csrf_token'] = secrets.token_hex(32)
            
            return render_template_string(
                LOGIN_TEMPLATE,
                username=username,
                token=session['csrf_token'],
                message="Неверное имя пользователя или пароль.",
                message_type="error"
            )
    else:
        session['csrf_token'] = secrets.token_hex(32)
        return render_template_string(
            LOGIN_TEMPLATE,
            username=username,
            token=session['csrf_token'],
            message="Введите имя пользователя и пароль.",
            message_type="error"
        )

if __name__ == "__main__":
    init_db()
    print("Запуск")
    print("URL: http://localhost:8082/vulnerabilities/brute/")
    app.run(host="0.0.0.0", port=8082, debug=False)
    
    