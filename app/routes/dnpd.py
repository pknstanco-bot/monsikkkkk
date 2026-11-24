import os
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_from_directory, abort
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.models import db, SuratTugas, LogAktivitas

dnpd_bp = Blueprint('dnpd', __name__)

@dnpd_bp.route('/arsip')
@login_required
def arsip():
    """Halaman Arsip Dokumen DNPD untuk Bendahara & Pengguna"""
    search = request.args.get('q', '').strip()
    status_doc = request.args.get('status') # 'ada' atau 'belum'
    
    query = SuratTugas.query
    
    if status_doc == 'ada':
        query = query.filter(SuratTugas.dnpd_filename.isnot(None))
    elif status_doc == 'belum':
        query = query.filter(SuratTugas.dnpd_filename.is_(None))
        
    if search:
        query = query.filter(
            (SuratTugas.nomor_st.ilike(f'%{search}%')) |
            (SuratTugas.maksud_tugas.ilike(f'%{search}%')) |
            (SuratTugas.kota_tujuan.ilike(f'%{search}%')) |
            (SuratTugas.dnpd_original_name.ilike(f'%{search}%'))
        )
        
    st_list = query.order_by(SuratTugas.tanggal_st.desc()).all()
    
    total_st = SuratTugas.query.count()
    total_dnpd_ada = SuratTugas.query.filter(SuratTugas.dnpd_filename.isnot(None)).count()
    total_dnpd_belum = total_st - total_dnpd_ada

    return render_template(
        'dnpd/arsip.html',
        st_list=st_list,
        total_st=total_st,
        total_dnpd_ada=total_dnpd_ada,
        total_dnpd_belum=total_dnpd_belum,
        search=search,
        status_doc=status_doc
    )

@dnpd_bp.route('/upload/<int:st_id>', methods=['POST'])
@login_required
def upload(st_id):
    st = SuratTugas.query.get_or_404(st_id)
    
    if 'dnpd_file' not in request.files:
        flash('Tidak ada file yang dipilih untuk diunggah.', 'warning')
        return redirect(request.referrer or url_for('dnpd.arsip'))
        
    file = request.files['dnpd_file']
    if file.filename == '':
        flash('Silakan pilih berkas dokumen DNPD.', 'warning')
        return redirect(request.referrer or url_for('dnpd.arsip'))
        
    orig_filename = secure_filename(file.filename)
    ext = orig_filename.rsplit('.', 1)[1].lower() if '.' in orig_filename else ''
    
    if ext not in current_app.config['ALLOWED_EXTENSIONS']:
        flash(f'Format file .{ext} tidak diizinkan. Gunakan PDF, Word, Excel, atau JPG/PNG.', 'danger')
        return redirect(request.referrer or url_for('dnpd.arsip'))
        
    # Hapus file lama jika ada penggantian (replace)
    if st.dnpd_filename:
        old_path = os.path.join(current_app.config['DNPD_UPLOAD_FOLDER'], st.dnpd_filename)
        if os.path.exists(old_path):
            try:
                os.remove(old_path)
            except Exception:
                pass
                
    saved_filename = f"DNPD_ST_{st.id}_{int(datetime.utcnow().timestamp())}.{ext}"
    filepath = os.path.join(current_app.config['DNPD_UPLOAD_FOLDER'], saved_filename)
    file.save(filepath)
    
    st.dnpd_filename = saved_filename
    st.dnpd_original_name = orig_filename
    st.dnpd_uploaded_at = datetime.utcnow()
    st.dnpd_uploaded_by = current_user.nama_lengkap
    
    log = LogAktivitas(
        user_id=current_user.id,
        username=current_user.username,
        aktivitas=f'Upload dokumen DNPD ({orig_filename}) untuk ST {st.nomor_st}',
        modul='DNPD'
    )
    db.session.add(log)
    db.session.commit()
    
    flash(f'Dokumen DNPD untuk {st.nomor_st} berhasil disimpan permanen di storage/dnpd/{saved_filename}!', 'success')
    return redirect(request.referrer or url_for('dnpd.arsip'))

@dnpd_bp.route('/download/<int:st_id>')
@login_required
def download(st_id):
    st = SuratTugas.query.get_or_404(st_id)
    if not st.dnpd_filename:
        flash('Dokumen DNPD belum tersedia untuk Surat Tugas ini.', 'warning')
        return redirect(request.referrer or url_for('dnpd.arsip'))
        
    folder = current_app.config['DNPD_UPLOAD_FOLDER']
    return send_from_directory(
        folder,
        st.dnpd_filename,
        as_attachment=True,
        download_name=st.dnpd_original_name or st.dnpd_filename
    )

@dnpd_bp.route('/preview/<int:st_id>')
@login_required
def preview(st_id):
    st = SuratTugas.query.get_or_404(st_id)
    if not st.dnpd_filename:
        abort(404)
        
    folder = current_app.config['DNPD_UPLOAD_FOLDER']
    return send_from_directory(
        folder,
        st.dnpd_filename,
        as_attachment=False
    )

@dnpd_bp.route('/delete/<int:st_id>', methods=['POST'])
@login_required
def delete(st_id):
    if not current_user.is_bendahara:
        flash('Akses ditolak. Hanya Bendahara/Admin yang dapat menghapus berkas DNPD.', 'danger')
        return redirect(request.referrer or url_for('dnpd.arsip'))
        
    st = SuratTugas.query.get_or_404(st_id)
    if st.dnpd_filename:
        filepath = os.path.join(current_app.config['DNPD_UPLOAD_FOLDER'], st.dnpd_filename)
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except Exception:
                pass
                
        nama_berkas = st.dnpd_original_name or st.dnpd_filename
        st.dnpd_filename = None
        st.dnpd_original_name = None
        st.dnpd_uploaded_at = None
        st.dnpd_uploaded_by = None
        
        log = LogAktivitas(
            user_id=current_user.id,
            username=current_user.username,
            aktivitas=f'Menghapus dokumen DNPD {nama_berkas} dari ST {st.nomor_st}',
            modul='DNPD'
        )
        db.session.add(log)
        db.session.commit()
        flash(f'Dokumen DNPD {nama_berkas} berhasil dihapus.', 'info')
        
    return redirect(request.referrer or url_for('dnpd.arsip'))
