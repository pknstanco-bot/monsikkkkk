from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.models import db, User, LogAktivitas

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
        
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        remember = bool(request.form.get('remember'))
        
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            if not user.is_active:
                flash('Akun Anda dinonaktifkan. Silakan hubungi Administrator.', 'danger')
                return render_template('auth/login.html')
                
            login_user(user, remember=remember)
            log = LogAktivitas(
                user_id=user.id,
                username=user.username,
                aktivitas=f'User {user.username} ({user.role}) berhasil login ke sistem',
                modul='AUTH'
            )
            db.session.add(log)
            db.session.commit()
            
            flash(f'Selamat datang kembali, {user.nama_lengkap}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard.index'))
        else:
            flash('Username atau password salah. Cek akun demo di bawah!', 'danger')
            
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    log = LogAktivitas(
        user_id=current_user.id,
        username=current_user.username,
        aktivitas=f'User {current_user.username} logout dari sistem',
        modul='AUTH'
    )
    db.session.add(log)
    db.session.commit()
    logout_user()
    flash('Anda telah berhasil keluar dari sistem MONSIK.', 'info')
    return redirect(url_for('auth.login'))
