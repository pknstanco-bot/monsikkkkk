import os
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, abort
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.models import db, SuratTugas, PesertaST, User, LogAktivitas

st_bp = Blueprint('surat_tugas', __name__)

@st_bp.route('/')
@login_required
def index():
    status_filter = request.args.get('status')
    lpj_filter = request.args.get('lpj')
    jenis_filter = request.args.get('jenis')
    search = request.args.get('q', '').strip()

    query = SuratTugas.query

    # Jika role PEGAWAI: Hanya tampilkan Surat Tugas miliknya
    if current_user.role == 'PEGAWAI':
        query = query.join(PesertaST).filter(
            (PesertaST.user_id == current_user.id) |
            (PesertaST.nip == current_user.nip) |
            (PesertaST.nama_pegawai == current_user.nama_lengkap)
        ).distinct()

    if jenis_filter:
        query = query.filter(SuratTugas.jenis_surat == jenis_filter)
    if status_filter:
        query = query.filter_by(status_pencairan=status_filter)
    if lpj_filter:
        query = query.filter_by(status_lpj=lpj_filter)
    if search:
        query = query.filter(
            (SuratTugas.nomor_st.ilike(f'%{search}%')) |
            (SuratTugas.maksud_tugas.ilike(f'%{search}%')) |
            (SuratTugas.kota_tujuan.ilike(f'%{search}%'))
        )

    page = request.args.get('page', 1, type=int)
    per_page = 10
    pagination = query.order_by(SuratTugas.tanggal_st.desc()).paginate(page=page, per_page=per_page, error_out=False)
    st_list = pagination.items
    return render_template(
        'surat_tugas/index.html',
        st_list=st_list,
        pagination=pagination,
        search=search,
        status_filter=status_filter,
        jenis_filter=jenis_filter
    )

@st_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    users = User.query.filter_by(is_active=True).order_by(User.nama_lengkap).all()
    
    if request.method == 'POST':
        nomor_st = request.form.get('nomor_st', '').strip()
        nomor_spd = request.form.get('nomor_spd', '').strip()
        maksud_tugas = (request.form.get('nama_st') or request.form.get('maksud_tugas', '')).strip()
        tanggal_st_str = request.form.get('tanggal_st')
        tempat_tujuan = request.form.get('tempat_tujuan', '').strip() or '-'
        kota_tujuan = request.form.get('kota_tujuan', '').strip() or '-'
        tgl_berangkat_str = request.form.get('tanggal_berangkat')
        tgl_kembali_str = request.form.get('tanggal_kembali')
        tingkat_biaya = request.form.get('tingkat_biaya', 'Tingkat B')
        akun_anggaran = request.form.get('akun_anggaran', '524111')
        catatan = request.form.get('catatan', '')

        # Validasi Input Minimal
        if not nomor_st or not maksud_tugas:
            flash('Nomor ST dan Nama ST wajib diisi!', 'danger')
            return redirect(request.referrer or url_for('surat_tugas.index'))

        # Validasi Nomor ST Unik
        if SuratTugas.query.filter_by(nomor_st=nomor_st).first():
            flash(f'Nomor ST {nomor_st} sudah pernah terdaftar!', 'danger')
            return redirect(request.referrer or url_for('surat_tugas.index'))

        from datetime import date
        today = date.today()
        try:
            tgl_st = datetime.strptime(tanggal_st_str, '%Y-%m-%d').date() if tanggal_st_str else today
        except Exception:
            tgl_st = today

        try:
            tgl_berangkat = datetime.strptime(tgl_berangkat_str, '%Y-%m-%d').date() if tgl_berangkat_str else today
            tgl_kembali = datetime.strptime(tgl_kembali_str, '%Y-%m-%d').date() if tgl_kembali_str else today
            jumlah_hari = max(1, (tgl_kembali - tgl_berangkat).days + 1)
        except Exception:
            tgl_berangkat = today
            tgl_kembali = today
            jumlah_hari = 1

        jenis_surat = request.form.get('jenis_surat', 'SIK').upper()
        if jenis_surat not in ['SIK', 'SPD']:
            jenis_surat = 'SIK'

        # Buat Instance SuratTugas
        st = SuratTugas(
            nomor_st=nomor_st,
            nomor_spd=nomor_spd or f"SPD/{nomor_st.replace('/', '-')}",
            jenis_surat=jenis_surat,
            progress_status='MERAH',
            tanggal_st=tgl_st,
            maksud_tugas=maksud_tugas,
            tempat_tujuan=tempat_tujuan,
            kota_tujuan=kota_tujuan,
            tanggal_berangkat=tgl_berangkat,
            tanggal_kembali=tgl_kembali,
            jumlah_hari=jumlah_hari,
            tingkat_biaya=tingkat_biaya,
            akun_anggaran=akun_anggaran,
            catatan=catatan,
            created_by_id=current_user.id
        )
        db.session.add(st)
        db.session.flush()

        # Proses Peserta ST (Golongan tidak usah)
        nama_list = request.form.getlist('peserta_nama[]')
        nip_list = request.form.getlist('peserta_nip[]')
        uang_harian_list = request.form.getlist('peserta_uang_harian[]')
        transport_list = request.form.getlist('peserta_transport[]')
        penginapan_list = request.form.getlist('peserta_penginapan[]')
        peran_list = request.form.getlist('peserta_peran[]')

        # Jika peserta diinput sebagai string tunggal / koma
        if not any(n.strip() for n in nama_list):
            single_peserta = request.form.get('peserta_nama', '').strip()
            if single_peserta:
                nama_list = [p.strip() for p in single_peserta.split(',') if p.strip()]

        # Jika tetap kosong, gunakan user yang login sebagai peserta default
        if not any(n.strip() for n in nama_list):
            nama_list = [current_user.nama_lengkap]
            nip_list = [current_user.nip or '']

        for i in range(len(nama_list)):
            p_nama = nama_list[i].strip()
            if p_nama:
                p_nip = nip_list[i].strip() if i < len(nip_list) else ''
                uh = 0.0
                if i < len(uang_harian_list) and uang_harian_list[i]:
                    try:
                        raw_uh = str(uang_harian_list[i]).replace('.', '').replace(',', '').strip()
                        uh = float(raw_uh) if raw_uh else 0.0
                    except ValueError:
                        uh = 0.0

                tr = 0.0
                if i < len(transport_list) and transport_list[i]:
                    try:
                        tr = float(str(transport_list[i]).replace('.', '').replace(',', '').strip())
                    except ValueError:
                        tr = 0.0

                pg = 0.0
                if i < len(penginapan_list) and penginapan_list[i]:
                    try:
                        pg = float(str(penginapan_list[i]).replace('.', '').replace(',', '').strip())
                    except ValueError:
                        pg = 0.0

                # Cocokkan dengan user terdaftar jika ada
                user_match = User.query.filter(
                    (User.nama_lengkap.ilike(p_nama)) |
                    (User.nip == p_nip if p_nip else False)
                ).first()

                peserta = PesertaST(
                    surat_tugas_id=st.id,
                    user_id=user_match.id if user_match else None,
                    nama_pegawai=p_nama,
                    nip=p_nip or (user_match.nip if user_match else None),
                    golongan=None, # Golongan tidak diperlukan
                    jabatan=user_match.jabatan if user_match else None,
                    peran=peran_list[i] if i < len(peran_list) else ('Ketua Tim' if i == 0 else 'Anggota'),
                    uang_harian_per_hari=uh,
                    jumlah_hari=jumlah_hari,
                    total_uang_harian=uh, # Langsung angka saja tanpa perkalian hari
                    biaya_transport=tr,
                    biaya_penginapan=pg,
                    biaya_lain=0.0
                )
                peserta.hitung_total()
                db.session.add(peserta)

        db.session.flush()
        st.hitung_total_anggaran()
        st.update_status_pencairan()

        # Handle File Upload DNPD jika ada
        if 'dnpd_file' in request.files:
            file = request.files['dnpd_file']
            if file and file.filename != '':
                orig_filename = secure_filename(file.filename)
                ext = orig_filename.rsplit('.', 1)[1].lower() if '.' in orig_filename else ''
                if ext in current_app.config['ALLOWED_EXTENSIONS']:
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
            aktivitas=f'Membuat Surat Tugas: {st.nomor_st} - {st.maksud_tugas}',
            modul='SURAT_TUGAS'
        )
        db.session.add(log)
        db.session.commit()

        flash(f'Surat Tugas {st.nomor_st} berhasil dibuat dengan {len(st.peserta_list)} peserta!', 'success')
        return redirect(request.referrer or url_for('surat_tugas.detail', id=st.id))

    return render_template('surat_tugas/create.html', users=users)

@st_bp.route('/<int:id>')
@login_required
def detail(id):
    st = SuratTugas.query.get_or_404(id)
    return render_template('surat_tugas/detail.html', st=st)

@st_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    st = SuratTugas.query.get_or_404(id)
    users = User.query.filter_by(is_active=True).order_by(User.nama_lengkap).all()

    if request.method == 'POST':
        st.nomor_st = request.form.get('nomor_st', '').strip()
        st.nomor_spd = request.form.get('nomor_spd', '').strip()
        tgl_st_str = request.form.get('tanggal_st')
        st.maksud_tugas = request.form.get('maksud_tugas', '').strip()
        st.tempat_tujuan = request.form.get('tempat_tujuan', '').strip()
        st.kota_tujuan = request.form.get('kota_tujuan', '').strip()
        tgl_berangkat_str = request.form.get('tanggal_berangkat')
        tgl_kembali_str = request.form.get('tanggal_kembali')
        st.tingkat_biaya = request.form.get('tingkat_biaya', 'Tingkat B')
        st.akun_anggaran = request.form.get('akun_anggaran', '524111')
        st.status_lpj = request.form.get('status_lpj', st.status_lpj)
        st.catatan = request.form.get('catatan', '')

        try:
            st.tanggal_st = datetime.strptime(tgl_st_str, '%Y-%m-%d').date()
            st.tanggal_berangkat = datetime.strptime(tgl_berangkat_str, '%Y-%m-%d').date()
            st.tanggal_kembali = datetime.strptime(tgl_kembali_str, '%Y-%m-%d').date()
            st.jumlah_hari = max(1, (st.tanggal_kembali - st.tanggal_berangkat).days + 1)
        except Exception as e:
            flash(f'Format tanggal salah: {str(e)}', 'danger')
            return render_template('surat_tugas/edit.html', st=st, users=users)

        # Hapus peserta lama dan replace dengan input baru
        PesertaST.query.filter_by(surat_tugas_id=st.id).delete()

        nama_list = request.form.getlist('peserta_nama[]')
        nip_list = request.form.getlist('peserta_nip[]')
        gol_list = request.form.getlist('peserta_gol[]')
        jabatan_list = request.form.getlist('peserta_jabatan[]')
        peran_list = request.form.getlist('peserta_peran[]')
        uang_harian_list = request.form.getlist('peserta_uang_harian[]')
        transport_list = request.form.getlist('peserta_transport[]')
        penginapan_list = request.form.getlist('peserta_penginapan[]')
        lain_list = request.form.getlist('peserta_lain[]')

        for i in range(len(nama_list)):
            if nama_list[i].strip():
                try:
                    uh = float(uang_harian_list[i] or 0)
                except ValueError:
                    uh = 430000.0
                try:
                    tr = float(transport_list[i] or 0)
                except ValueError:
                    tr = 0.0
                try:
                    pg = float(penginapan_list[i] or 0)
                except ValueError:
                    pg = 0.0
                try:
                    ln = float(lain_list[i] or 0)
                except ValueError:
                    ln = 0.0

                user_match = User.query.filter(
                    (User.nama_lengkap.ilike(nama_list[i].strip())) |
                    (User.nip == nip_list[i].strip())
                ).first()

                peserta = PesertaST(
                    surat_tugas_id=st.id,
                    user_id=user_match.id if user_match else None,
                    nama_pegawai=nama_list[i].strip(),
                    nip=nip_list[i].strip(),
                    golongan=gol_list[i].strip(),
                    jabatan=jabatan_list[i].strip(),
                    peran=peran_list[i] if i < len(peran_list) else 'Anggota',
                    uang_harian_per_hari=uh,
                    jumlah_hari=st.jumlah_hari,
                    biaya_transport=tr,
                    biaya_penginapan=pg,
                    biaya_lain=ln
                )
                peserta.hitung_total()
                db.session.add(peserta)

        db.session.flush()
        st.hitung_total_anggaran()
        st.update_status_pencairan()

        log = LogAktivitas(
            user_id=current_user.id,
            username=current_user.username,
            aktivitas=f'Memperbarui data Surat Tugas: {st.nomor_st}',
            modul='SURAT_TUGAS'
        )
        db.session.add(log)
        db.session.commit()

        flash(f'Surat Tugas {st.nomor_st} berhasil diperbarui!', 'success')
        return redirect(url_for('surat_tugas.detail', id=st.id))

    return render_template('surat_tugas/edit.html', st=st, users=users)

@st_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    if not current_user.is_admin:
        flash('Hanya Administrator yang memiliki wewenang menghapus Surat Tugas.', 'danger')
        return redirect(url_for('surat_tugas.index'))

    st = SuratTugas.query.get_or_404(id)
    nomor = st.nomor_st

    # Hapus file fisik DNPD jika ada
    if st.dnpd_filename:
        filepath = os.path.join(current_app.config['DNPD_UPLOAD_FOLDER'], st.dnpd_filename)
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except Exception:
                pass

    db.session.delete(st)
    log = LogAktivitas(
        user_id=current_user.id,
        username=current_user.username,
        aktivitas=f'Menghapus Surat Tugas: {nomor}',
        modul='SURAT_TUGAS'
    )
    db.session.add(log)
    db.session.commit()

    flash(f'Surat Tugas {nomor} beserta peserta dan riwayat pencairannya berhasil dihapus.', 'info')
    return redirect(url_for('surat_tugas.index'))

@st_bp.route('/update-progress/<int:id>', methods=['POST'])
@login_required
def update_progress(id):
    if not current_user.is_admin:
        flash('Hanya Administrator yang memiliki wewenang mengubah status progress penugasan.', 'danger')
        return redirect(request.referrer or url_for('surat_tugas.index'))

    st = SuratTugas.query.get_or_404(id)
    new_progress = request.form.get('progress_status', '').upper()
    
    if new_progress in ['MERAH', 'KUNING', 'HIJAU']:
        st.progress_status = new_progress
        
        # Jika hijau, tandai juga status LPJ surat tugas selesai dan sisa belum cair langsung masuk ke telah dicairkan
        if new_progress == 'HIJAU':
            st.status_lpj = 'SELESAI'
            st.status_pencairan = 'CAIR_PENUH'
            st.total_dicairkan = st.total_anggaran
            for p in st.peserta_list:
                p.status_lpj_peserta = 'SELESAI'
        elif new_progress == 'KUNING':
            st.status_lpj = 'MENUNGGU_VERIFIKASI'
            st.update_status_pencairan()
            for p in st.peserta_list:
                if p.status_lpj_peserta != 'SELESAI':
                    p.status_lpj_peserta = 'MENUNGGU_VERIFIKASI'
        elif new_progress == 'MERAH':
            st.status_lpj = 'BELUM_LPJ'
            st.update_status_pencairan()

        labels = {
            'MERAH': 'Merah: Belum Upload Laporan & Sinkron Geotagging',
            'KUNING': 'Kuning: Sudah Upload Laporan Menunggu Pencairan',
            'HIJAU': 'Hijau: Telah Cair'
        }

        log = LogAktivitas(
            user_id=current_user.id,
            username=current_user.username,
            aktivitas=f'Update Progress ST {st.nomor_st} -> {labels.get(new_progress)}',
            modul='PROGRESS_ST'
        )
        db.session.add(log)
        db.session.commit()
        flash(f'Status progress {st.nomor_st} berhasil diperbarui: {labels.get(new_progress)}', 'success')

    return redirect(request.referrer or url_for('surat_tugas.index'))

@st_bp.route('/update-peserta-status/<int:peserta_id>', methods=['POST'])
@login_required
def update_peserta_status(peserta_id):
    if not current_user.is_admin:
        flash('Hanya Administrator yang memiliki wewenang mengubah status pertanggungjawaban peserta.', 'danger')
        return redirect(request.referrer or url_for('surat_tugas.index'))

    peserta = PesertaST.query.get_or_404(peserta_id)
    new_status = request.form.get('status_lpj_peserta', '').upper()
    
    if new_status in ['BELUM_LPJ', 'MENUNGGU_VERIFIKASI', 'SELESAI']:
        peserta.status_lpj_peserta = new_status
        db.session.commit()
        flash(f'Status pertanggungjawaban peserta {peserta.nama_pegawai} berhasil diperbarui!', 'success')

    return redirect(request.referrer or url_for('surat_tugas.detail', id=peserta.surat_tugas_id))
