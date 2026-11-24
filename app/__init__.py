import os
from datetime import datetime, date
from flask import Flask, redirect, url_for, render_template
from flask_login import LoginManager, current_user
from app.config import config
from app.models import db, User, SuratTugas, PesertaST, Pencairan, LogAktivitas

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Silakan login terlebih dahulu untuk mengakses halaman ini.'
login_manager.login_message_category = 'warning'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def format_rupiah(value):
    if value is None:
        return "Rp 0"
    try:
        val = float(value)
        return f"Rp {val:,.0f}".replace(",", ".")
    except (ValueError, TypeError):
        return str(value)

def format_tanggal(value, fmt="%d %b %Y"):
    if not value:
        return "-"
    if isinstance(value, str):
        try:
            value = datetime.strptime(value, "%Y-%m-%d").date()
        except Exception:
            return value
    if isinstance(value, (datetime, date)):
        bulan_indo = {
            1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "Mei", 6: "Jun",
            7: "Jul", 8: "Agu", 9: "Sep", 10: "Okt", 11: "Nov", 12: "Des"
        }
        return f"{value.day:02d} {bulan_indo[value.month]} {value.year}"
    return str(value)

def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG', 'development')
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Pastikan folder instance dan storage/dnpd selalu ada
    os.makedirs(app.config['INSTANCE_DIR'], exist_ok=True)
    os.makedirs(app.config['DNPD_UPLOAD_FOLDER'], exist_ok=True)

    # Inisialisasi ekstensi
    db.init_app(app)
    login_manager.init_app(app)

    # Filter Jinja kustom
    app.jinja_env.filters['rupiah'] = format_rupiah
    app.jinja_env.filters['tanggal'] = format_tanggal

    @app.context_processor
    def inject_global_data():
        from flask_login import current_user
        if current_user and current_user.is_authenticated:
            registered_users = User.query.filter_by(is_active=True).all()
        else:
            registered_users = []
        return {'registered_users': registered_users}

    # Register Blueprints
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.surat_tugas import st_bp
    from app.routes.pencairan import pencairan_bp
    from app.routes.monitoring import monitoring_bp
    from app.routes.dnpd import dnpd_bp
    from app.routes.export import export_bp
    from app.routes.users import users_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(dashboard_bp, url_prefix='/')
    app.register_blueprint(st_bp, url_prefix='/surat-tugas')
    app.register_blueprint(pencairan_bp, url_prefix='/pencairan')
    app.register_blueprint(monitoring_bp, url_prefix='/monitoring')
    app.register_blueprint(dnpd_bp, url_prefix='/dnpd')
    app.register_blueprint(export_bp, url_prefix='/export')
    app.register_blueprint(users_bp, url_prefix='/users')

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template('errors/500.html'), 500

    # Auto-inisialisasi database & seed user default saat start
    with app.app_context():
        db.create_all()
        seed_default_data()

    return app

def seed_default_data():
    """Inisialisasi akun bawaan dan data master pegawai dari PEGAWAI.xlsx jika database baru"""
    # 1. Pastikan User Default Admin & Bendahara Ada
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(
            username='admin',
            nama_lengkap='Administrator Monsik',
            nip='198501012010011001',
            jabatan='Koordinator Perencanaan & Keuangan',
            golongan='IV/a',
            role='ADMIN'
        )
        admin.set_password('admin123')
        db.session.add(admin)

    bendahara = User.query.filter_by(username='bendahara').first()
    if not bendahara:
        bendahara = User(
            username='bendahara',
            nama_lengkap='Ayudari',
            nip='198804152012012003',
            jabatan='Bendahara Pengeluaran',
            golongan='III/c',
            role='BENDAHARA'
        )
        bendahara.set_password('bendahara123')
        db.session.add(bendahara)

    db.session.commit()

    # 2. Import Master Pegawai dari PEGAWAI.xlsx jika ada dan data pegawai masih kosong
    excel_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'PEGAWAI.xlsx')
    if os.path.exists(excel_path) and User.query.filter_by(role='PEGAWAI').count() == 0:
        import openpyxl
        try:
            from werkzeug.security import generate_password_hash
            cached_hash = generate_password_hash('123456')
            wb = openpyxl.load_workbook(excel_path, data_only=True)
            ws = wb.active
            for row in ws.iter_rows(min_row=2, max_row=ws.max_row, values_only=True):
                nama_raw = str(row[2]).strip() if row[2] is not None else ''
                proper_col = str(row[3]).strip() if row[3] is not None else ''
                nip_raw = str(row[4]).strip() if row[4] is not None else ''
                if isinstance(row[4], float):
                    nip_raw = f"{int(row[4])}"

                nama_final = proper_col if proper_col and proper_col != 'None' and not proper_col.startswith('=') else nama_raw
                if not nama_final or not nip_raw:
                    continue

                username = nip_raw
                if not User.query.filter_by(username=username).first():
                    u = User(
                        username=username,
                        nama_lengkap=nama_final,
                        nip=nip_raw,
                        jabatan='Pegawai',
                        role='PEGAWAI',
                        password_hash=cached_hash
                    )
                    db.session.add(u)
            db.session.commit()
        except Exception as e:
            print(f"Error seeding PEGAWAI.xlsx: {e}")
