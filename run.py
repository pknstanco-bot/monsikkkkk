import os
import sys

# Tambahkan direktori root aplikasi ke sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app

# Konfigurasi environment: 'development' atau 'production'
config_name = os.environ.get('FLASK_CONFIG', 'development')
app = create_app(config_name)

if __name__ == '__main__':
    host = app.config.get('HOST', '127.0.0.1')
    port = app.config.get('PORT', 5010)
    
    print("=" * 65)
    print("        MONSIK - MONITORING SIK & SPD SERVER")
    print("=" * 65)
    print(f" Environment : {config_name.upper()}")
    print(f" Database    : {app.config.get('SQLALCHEMY_DATABASE_URI')}")
    print(f" Storage DNPD: {app.config.get('DNPD_UPLOAD_FOLDER')}")
    print("=" * 65)
    print(f" Server Aktif! Silakan buka browser:")
    print(f"  >>> http://{host}:{port}")
    if host == '0.0.0.0':
        print(f"  >>> http://127.0.0.1:{port} (Akses Lokal)")
        print(f"  >>> http://<IP-KOMPUTER-ANDA>:{port} (Akses Jaringan LAN)")
    print("=" * 65)
    print(" Tekan CTRL + C untuk menghentikan server.")
    print("=" * 65)
    
    app.run(host=host, port=port, debug=app.config.get('DEBUG', True))
