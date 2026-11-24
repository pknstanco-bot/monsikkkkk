from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import db, User, LogAktivitas

users_bp = Blueprint('users', __name__)

@users_bp.route('/')
@login_required
def index():
    if not current_user.is_admin:
        flash('Akses terbatas hanya untuk Administrator.', 'danger')
        return redirect(url_for('dashboard.index'))
        
    user_list = User.query.order_by(User.id.asc()).all()
    return render_template('users/index.html', user_list=user_list)

@users_bp.route('/create', methods=['POST'])
@login_required
def create():
    if not current_user.is_admin:
        flash('Hanya Administrator yang dapat menambah user.', 'danger')
        return redirect(url_for('users.index'))

    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    nama = request.form.get('nama_lengkap', '').strip()
    nip = request.form.get('nip', '').strip()
    jabatan = request.form.get('jabatan', '').strip()
    golongan = request.form.get('golongan', '').strip()
    role = request.form.get('role', 'PEGAWAI')

    if User.query.filter_by(username=username).first():
        flash(f'Username {username} sudah digunakan!', 'danger')
        return redirect(url_for('users.index'))

    new_user = User(
        username=username,
        nama_lengkap=nama,
        nip=nip,
        jabatan=jabatan,
        golongan=golongan,
        role=role
    )
    new_user.set_password(password or 'password123')
    db.session.add(new_user)
    
    log = LogAktivitas(
        user_id=current_user.id,
        username=current_user.username,
        aktivitas=f'Menambahkan user baru: {username} ({role})',
        modul='USER_MGMT'
    )
    db.session.add(log)
    db.session.commit()

    flash(f'User {nama} ({username}) berhasil ditambahkan.', 'success')
    return redirect(url_for('users.index'))

@users_bp.route('/<int:id>/toggle-status', methods=['POST'])
@login_required
def toggle_status(id):
    if not current_user.is_admin:
        flash('Hanya Administrator yang memiliki akses.', 'danger')
        return redirect(url_for('users.index'))

    user = User.query.get_or_404(id)
    if user.id == current_user.id:
        flash('Anda tidak dapat menonaktifkan akun sendiri.', 'warning')
        return redirect(url_for('users.index'))

    user.is_active = not user.is_active
    db.session.commit()
    status_str = "diaktifkan" if user.is_active else "dinonaktifkan"
    flash(f'Status akun {user.username} berhasil {status_str}.', 'info')
    return redirect(url_for('users.index'))

@users_bp.route('/<int:id>/reset-password', methods=['POST'])
@login_required
def reset_password(id):
    if not current_user.is_admin:
        flash('Hanya Administrator yang memiliki akses.', 'danger')
        return redirect(url_for('users.index'))

    user = User.query.get_or_404(id)
    new_pw = request.form.get('new_password', 'password123')
    user.set_password(new_pw)
    db.session.commit()

    flash(f'Password untuk {user.username} berhasil di-reset menjadi "{new_pw}".', 'success')
    return redirect(url_for('users.index'))
