import os
from datetime import datetime

class BaseConfig:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'monsik-secret-key-2026-supersecure')
    BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    
    # SQLite Database Location: instance/monsik.db
    INSTANCE_DIR = os.path.join(BASE_DIR, 'instance')
    
    # Khusus environment Vercel serverless (filesystem read-only, writeable di /tmp)
    if os.environ.get('VERCEL'):
        import shutil
        TMP_DIR = '/tmp'
        TMP_DB = os.path.join(TMP_DIR, 'monsik.db')
        SRC_DB = os.path.join(INSTANCE_DIR, 'monsik.db')
        if not os.path.exists(TMP_DB) and os.path.exists(SRC_DB):
            try:
                shutil.copy2(SRC_DB, TMP_DB)
            except Exception:
                pass
        SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or f'sqlite:///{TMP_DB}'
        DNPD_UPLOAD_FOLDER = os.path.join(TMP_DIR, 'dnpd')
        os.makedirs(DNPD_UPLOAD_FOLDER, exist_ok=True)
    else:
        SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or f'sqlite:///{os.path.join(INSTANCE_DIR, "monsik.db")}'
        # Storage Directory for DNPD Documents
        STORAGE_DIR = os.path.join(BASE_DIR, 'storage')
        DNPD_UPLOAD_FOLDER = os.path.join(STORAGE_DIR, 'dnpd')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 32 * 1024 * 1024  # Max 32 MB upload
    ALLOWED_EXTENSIONS = {'pdf', 'docx', 'doc', 'xlsx', 'xls', 'jpg', 'jpeg', 'png'}

    # Host & Port settings
    HOST = os.environ.get('FLASK_HOST', '127.0.0.1')
    PORT = int(os.environ.get('FLASK_PORT', 5010))

class DevelopmentConfig(BaseConfig):
    DEBUG = True
    ENV = 'development'

class ProductionConfig(BaseConfig):
    DEBUG = False
    ENV = 'production'
    # Pada server kantor, HOST dapat di-set 0.0.0.0 via env atau config
    HOST = os.environ.get('FLASK_HOST', '0.0.0.0')

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
