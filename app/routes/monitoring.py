from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy import func
from app.models import db, SuratTugas, PesertaST, User

monitoring_bp = Blueprint('monitoring', __name__)

@monitoring_bp.route('/pegawai')
@login_required
def pegawai():
    # Menu ini khusus untuk Administrator dan Bendahara
    if current_user.role == 'PEGAWAI':
        flash('Menu Monitoring Seluruh Pegawai hanya dapat diakses oleh Administrator dan Bendahara.', 'warning')
        return redirect(url_for('dashboard.index'))

    search = request.args.get('q', '').strip()
    
    query = PesertaST.query.join(SuratTugas)
    if search:
        query = query.filter(
            (PesertaST.nama_pegawai.ilike(f'%{search}%')) |
            (PesertaST.nip.ilike(f'%{search}%')) |
            (PesertaST.jabatan.ilike(f'%{search}%'))
        )

    all_peserta = query.all()

    # Hitung akumulasi per pegawai: Uang Harian langsung (tanpa dikali hari), Telah Cair, dan Belum Cair
    pegawai_dict = {}
    for p in all_peserta:
        key = (p.nama_pegawai, p.nip or '', p.jabatan or '', p.golongan or '')
        if key not in pegawai_dict:
            pegawai_dict[key] = {
                'nama_pegawai': p.nama_pegawai,
                'nip': p.nip,
                'jabatan': p.jabatan,
                'golongan': p.golongan,
                'total_st': 0,
                'total_uh': 0.0,
                'total_cair': 0.0,
                'total_belum_cair': 0.0,
                'total_biaya': 0.0
            }

        st = p.surat_tugas
        biaya_p = p.total_biaya_peserta or 0.0
        # Pakai uang hariannya langsung tanpa dikalikan total hari dinas
        uh_p = p.total_uang_harian or p.uang_harian_per_hari or 0.0

        # Hitung bagian nominal telah cair dan belum cair
        if st.progress_status == 'HIJAU' or st.status_pencairan == 'CAIR_PENUH':
            cair_p = biaya_p
            belum_cair_p = 0.0
        elif st.status_pencairan == 'OUTSTANDING':
            cair_p = 0.0
            belum_cair_p = biaya_p
        elif st.status_pencairan == 'CAIR_SEBAGIAN':
            ratio = (st.total_dicairkan / st.total_anggaran) if (st.total_anggaran and st.total_anggaran > 0) else 0.0
            ratio = min(1.0, max(0.0, ratio))
            cair_p = biaya_p * ratio
            belum_cair_p = max(0.0, biaya_p - cair_p)
        else:
            cair_p = 0.0
            belum_cair_p = biaya_p

        pegawai_dict[key]['total_st'] += 1
        pegawai_dict[key]['total_uh'] += uh_p
        pegawai_dict[key]['total_cair'] += cair_p
        pegawai_dict[key]['total_belum_cair'] += belum_cair_p
        pegawai_dict[key]['total_biaya'] += biaya_p

    pegawai_summary = sorted(pegawai_dict.values(), key=lambda x: x['total_st'], reverse=True)

    return render_template(
        'monitoring/pegawai.html',
        pegawai_summary=pegawai_summary,
        search=search
    )

@monitoring_bp.route('/uang-harian')
@login_required
def uang_harian():
    search = request.args.get('q', '').strip()
    
    query = PesertaST.query.join(SuratTugas)

    # Khusus Peserta ST (PEGAWAI): Hanya tampilkan data uang harian yang sesuai dengan dirinya
    if current_user.role == 'PEGAWAI':
        query = query.filter(
            (PesertaST.user_id == current_user.id) |
            (PesertaST.nip == current_user.nip) |
            (PesertaST.nama_pegawai == current_user.nama_lengkap)
        )

    if search:
        query = query.filter(
            (PesertaST.nama_pegawai.ilike(f'%{search}%')) |
            (SuratTugas.nomor_st.ilike(f'%{search}%')) |
            (SuratTugas.kota_tujuan.ilike(f'%{search}%'))
        )
        
    peserta_list = query.order_by(SuratTugas.tanggal_st.desc()).all()
    
    # Total uang harian keseluruhan
    total_uh = sum(p.total_uang_harian or 0.0 for p in peserta_list)
    total_hari = sum(p.jumlah_hari or 0 for p in peserta_list)
    
    return render_template(
        'monitoring/uang_harian.html',
        peserta_list=peserta_list,
        total_uh=total_uh,
        total_hari=total_hari,
        search=search
    )

@monitoring_bp.route('/lpj')
@login_required
def lpj():
    status_filter = request.args.get('status')
    
    query = SuratTugas.query
    if status_filter:
        query = query.filter_by(status_lpj=status_filter)
        
    st_list = query.order_by(SuratTugas.tanggal_st.desc()).all()
    
    count_belum = SuratTugas.query.filter_by(status_lpj='BELUM_LPJ').count()
    count_verif = SuratTugas.query.filter_by(status_lpj='MENUNGGU_VERIFIKASI').count()
    count_terverif = SuratTugas.query.filter_by(status_lpj='TERVERIFIKASI').count()
    count_selesai = SuratTugas.query.filter_by(status_lpj='SELESAI').count()

    return render_template(
        'monitoring/lpj.html',
        st_list=st_list,
        status_filter=status_filter,
        count_belum=count_belum,
        count_verif=count_verif,
        count_terverif=count_terverif,
        count_selesai=count_selesai
    )
