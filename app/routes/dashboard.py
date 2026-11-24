from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from sqlalchemy import func
from datetime import datetime, date
from app.models import db, SuratTugas, PesertaST, Pencairan, User

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@login_required
def index():
    # Filter berbasis Role: Jika PEGAWAI, hanya ST miliknya yang dihitung & ditampilkan
    base_query = SuratTugas.query
    if current_user.role == 'PEGAWAI':
        base_query = base_query.join(PesertaST).filter(
            (PesertaST.user_id == current_user.id) |
            (PesertaST.nip == current_user.nip) |
            (PesertaST.nama_pegawai == current_user.nama_lengkap)
        ).distinct()
    
    all_st = base_query.all()

    # Perhitungan 4 Metrik Pokok: SIK vs SPD (Outstanding vs Cair)
    sik_outstanding = 0.0
    spd_outstanding = 0.0
    sik_cair = 0.0
    spd_cair = 0.0

    count_sik_out = 0
    count_spd_out = 0
    count_sik_cair = 0
    count_spd_cair = 0

    for st in all_st:
        anggaran = st.get_anggaran_for_user(current_user)
        cair = st.get_cair_for_user(current_user)
        sisa = st.get_outstanding_for_user(current_user)

        if (st.jenis_surat or 'SIK').upper() == 'SPD':
            spd_outstanding += sisa
            spd_cair += cair
            if st.progress_status != 'HIJAU' and st.status_pencairan != 'CAIR_PENUH':
                count_spd_out += 1
            if cair > 0 or st.progress_status == 'HIJAU':
                count_spd_cair += 1
        else:
            # Default SIK (Dalam Kota)
            sik_outstanding += sisa
            sik_cair += cair
            if st.progress_status != 'HIJAU' and st.status_pencairan != 'CAIR_PENUH':
                count_sik_out += 1
            if cair > 0 or st.progress_status == 'HIJAU':
                count_sik_cair += 1

    # Filter jenis di tabel dashboard jika ada (SIK / SPD)
    jenis_filter = request.args.get('jenis')
    st_query = base_query
    if jenis_filter:
        st_query = st_query.filter(SuratTugas.jenis_surat == jenis_filter)

    # 3. Surat Tugas Terbaru (Limit 10)
    st_terbaru = st_query.order_by(SuratTugas.created_at.desc()).limit(10).all()
    
    # 4. Pencairan Terakhir
    pencairan_terbaru = Pencairan.query.order_by(Pencairan.created_at.desc()).limit(5).all()

    return render_template(
        'dashboard/index.html',
        sik_outstanding=sik_outstanding,
        spd_outstanding=spd_outstanding,
        sik_cair=sik_cair,
        spd_cair=spd_cair,
        count_sik_out=count_sik_out,
        count_spd_out=count_spd_out,
        count_sik_cair=count_sik_cair,
        count_spd_cair=count_spd_cair,
        total_st=len(all_st),
        st_terbaru=st_terbaru,
        pencairan_terbaru=pencairan_terbaru,
        jenis_filter=jenis_filter,
        today=date.today()
    )

@dashboard_bp.route('/api/stats-chart')
@login_required
def stats_chart():
    """Data endpoint untuk Chart.js di Dashboard"""
    # Mengambil sebaran status pencairan
    count_out = SuratTugas.query.filter_by(status_pencairan='OUTSTANDING').count()
    count_seb = SuratTugas.query.filter_by(status_pencairan='CAIR_SEBAGIAN').count()
    count_pen = SuratTugas.query.filter_by(status_pencairan='CAIR_PENUH').count()
    
    # Biaya per bulan (Jan - Des tahun berjalan)
    tahun_ini = date.today().year
    bulan_labels = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
    anggaran_per_bulan = [0.0] * 12
    cair_per_bulan = [0.0] * 12
    
    all_st = SuratTugas.query.all()
    for st in all_st:
        if st.tanggal_st and st.tanggal_st.year == tahun_ini:
            m = st.tanggal_st.month - 1
            anggaran_per_bulan[m] += (st.total_anggaran or 0.0)
            cair_per_bulan[m] += (st.total_dicairkan or 0.0)
            
    return jsonify({
        'status_distribution': {
            'labels': ['Outstanding (Belum Cair)', 'Cair Sebagian', 'Cair Penuh'],
            'data': [count_out, count_seb, count_pen]
        },
        'monthly_volume': {
            'labels': bulan_labels,
            'anggaran': anggaran_per_bulan,
            'cair': cair_per_bulan
        }
    })
