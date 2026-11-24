from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import db, SuratTugas, Pencairan, LogAktivitas

pencairan_bp = Blueprint('pencairan', __name__)

@pencairan_bp.route('/')
@login_required
def index():
    status = request.args.get('tab', 'semua')
    
    query = SuratTugas.query
    if current_user.role == 'PEGAWAI':
        from app.models import PesertaST
        query = query.join(PesertaST).filter(
            (PesertaST.user_id == current_user.id) |
            (PesertaST.nip == current_user.nip) |
            (PesertaST.nama_pegawai == current_user.nama_lengkap)
        ).distinct()
    
    if status == 'outstanding':
        st_list = query.filter_by(status_pencairan='OUTSTANDING').order_by(SuratTugas.tanggal_st.desc()).all()
    elif status == 'cair':
        st_list = query.filter(SuratTugas.status_pencairan.in_(['CAIR_SEBAGIAN', 'CAIR_PENUH'])).order_by(SuratTugas.tanggal_st.desc()).all()
    else:
        st_list = query.order_by(SuratTugas.tanggal_st.desc()).all()

    if current_user.role == 'PEGAWAI':
        st_ids = [st.id for st in st_list]
        pencairan_riwayat = Pencairan.query.filter(Pencairan.surat_tugas_id.in_(st_ids)).order_by(Pencairan.created_at.desc()).limit(15).all() if st_ids else []
    else:
        pencairan_riwayat = Pencairan.query.order_by(Pencairan.created_at.desc()).limit(15).all()

    return render_template(
        'pencairan/index.html',
        st_list=st_list,
        pencairan_riwayat=pencairan_riwayat,
        active_tab=status
    )

@pencairan_bp.route('/proses/<int:st_id>', methods=['POST'])
@login_required
def proses(st_id):
    if not current_user.is_bendahara:
        flash('Hanya Bendahara atau Administrator yang dapat memproses pencairan SIK/SPD!', 'danger')
        return redirect(url_for('pencairan.index'))

    st = SuratTugas.query.get_or_404(st_id)
    
    nomor_sp2d = request.form.get('nomor_sp2d', '').strip()
    tgl_cair_str = request.form.get('tanggal_cair')
    raw_val = request.form.get('jumlah_cair', '0').strip()
    jenis = request.form.get('jenis_pencairan', 'PENUH') # UANG_MUKA, PELUNASAN, PENUH
    metode = request.form.get('metode_bayar', 'Transfer Bank')
    catatan = request.form.get('catatan', '')

    if ',' in raw_val and '.' in raw_val:
        raw_val = raw_val.replace('.', '').replace(',', '.')
    elif '.' in raw_val and len(raw_val.split('.')[-1]) == 3: # Indonesian ribuan e.g. 500.000
        raw_val = raw_val.replace('.', '')
    elif ',' in raw_val:
        raw_val = raw_val.replace(',', '.')

    try:
        jumlah_cair = float(raw_val)
        tgl_cair = datetime.strptime(tgl_cair_str, '%Y-%m-%d').date()
    except Exception as e:
        flash(f'Input jumlah pencairan atau tanggal tidak valid: {str(e)}', 'danger')
        return redirect(request.referrer or url_for('pencairan.index'))

    if jumlah_cair <= 0:
        flash('Jumlah pencairan harus lebih besar dari 0!', 'warning')
        return redirect(request.referrer or url_for('pencairan.index'))

    sisa_anggaran = st.total_anggaran - st.total_dicairkan
    if jumlah_cair > sisa_anggaran and jenis != 'PELUNASAN':
        flash(f'Jumlah pencairan (Rp {jumlah_cair:,.0f}) melebihi sisa anggaran (Rp {sisa_anggaran:,.0f})!', 'warning')

    pencairan = Pencairan(
        surat_tugas_id=st.id,
        nomor_sp2d_kwitansi=nomor_sp2d,
        tanggal_cair=tgl_cair,
        jumlah_cair=jumlah_cair,
        jenis_pencairan=jenis,
        metode_bayar=metode,
        catatan=catatan,
        bendahara_id=current_user.id
    )
    db.session.add(pencairan)
    db.session.flush()

    # Update status ST
    st.update_status_pencairan()

    log = LogAktivitas(
        user_id=current_user.id,
        username=current_user.username,
        aktivitas=f'Pencairan dana {jenis} sebesar Rp {jumlah_cair:,.0f} untuk ST {st.nomor_st} (SP2D: {nomor_sp2d})',
        modul='PENCAIRAN'
    )
    db.session.add(log)
    db.session.commit()

    flash(f'Pencairan dana SIK/SPD untuk ST {st.nomor_st} berhasil dicatat (Rp {jumlah_cair:,.0f})!', 'success')
    return redirect(request.referrer or url_for('pencairan.index'))

@pencairan_bp.route('/batal/<int:cair_id>', methods=['POST'])
@login_required
def batal(cair_id):
    if not current_user.is_bendahara:
        flash('Akses ditolak. Hanya Bendahara/Admin yang dapat membatalkan transaksi pencairan.', 'danger')
        return redirect(url_for('pencairan.index'))

    cair = Pencairan.query.get_or_404(cair_id)
    st = cair.surat_tugas
    nominal = cair.jumlah_cair

    db.session.delete(cair)
    db.session.flush()

    st.update_status_pencairan()

    log = LogAktivitas(
        user_id=current_user.id,
        username=current_user.username,
        aktivitas=f'Membatalkan pencairan Rp {nominal:,.0f} pada ST {st.nomor_st}',
        modul='PENCAIRAN'
    )
    db.session.add(log)
    db.session.commit()

    flash(f'Transaksi pencairan Rp {nominal:,.0f} berhasil dibatalkan.', 'info')
    return redirect(request.referrer or url_for('pencairan.index'))
