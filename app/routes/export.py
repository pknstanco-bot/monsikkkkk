import io
from datetime import datetime, date
from flask import Blueprint, render_template, request, make_response, send_file, flash, redirect, url_for
from flask_login import login_required, current_user
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from app.models import SuratTugas, PesertaST, Pencairan

export_bp = Blueprint('export', __name__)

@export_bp.route('/excel/surat-tugas')
@login_required
def excel_surat_tugas():
    wb = Workbook()
    ws = wb.active
    ws.title = "Rekap SIK & SPD"

    # Styling header
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1B365D", end_color="1B365D", fill_type="solid")
    title_font = Font(name="Calibri", size=14, bold=True, color="1B365D")
    border_thin = Border(
        left=Side(style='thin', color='D0D5DD'),
        right=Side(style='thin', color='D0D5DD'),
        top=Side(style='thin', color='D0D5DD'),
        bottom=Side(style='thin', color='D0D5DD')
    )

    # Judul Dokumen
    ws.merge_cells("A1:K1")
    ws["A1"] = "DAFTAR MONITORING SURAT IZIN KEGIATAN & SURAT PERJALANAN DINAS (SIK & SPD)"
    ws["A1"].font = title_font
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")

    ws.merge_cells("A2:K2")
    ws["A2"] = f"Aplikasi MONSIK - Diekspor pada: {datetime.now().strftime('%d-%m-%Y %H:%M WIB')}"
    ws["A2"].alignment = Alignment(horizontal="center")

    headers = [
        "No", "Nomor ST", "Nomor SPD", "Tanggal ST", "Kota Tujuan",
        "Maksud Tugas", "Jml Hari", "Total Anggaran (Rp)",
        "Total Cair (Rp)", "Status Pencairan", "Status LPJ"
    ]

    row_num = 4
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=row_num, column=col_num)
        cell.value = header
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = border_thin

    query = SuratTugas.query
    if current_user.role == 'PEGAWAI':
        query = query.join(PesertaST).filter(
            (PesertaST.user_id == current_user.id) |
            (PesertaST.nip == current_user.nip) |
            (PesertaST.nama_pegawai == current_user.nama_lengkap)
        ).distinct()
    st_list = query.order_by(SuratTugas.tanggal_st.desc()).all()
    for idx, st in enumerate(st_list, 1):
        row_num += 1
        ws.cell(row=row_num, column=1, value=idx).alignment = Alignment(horizontal="center")
        ws.cell(row=row_num, column=2, value=st.nomor_st)
        ws.cell(row=row_num, column=3, value=st.nomor_spd or "-")
        ws.cell(row=row_num, column=4, value=st.tanggal_st.strftime('%d/%m/%Y') if st.tanggal_st else "-")
        ws.cell(row=row_num, column=5, value=st.kota_tujuan)
        ws.cell(row=row_num, column=6, value=st.maksud_tugas)
        ws.cell(row=row_num, column=7, value=st.jumlah_hari).alignment = Alignment(horizontal="center")
        
        c_anggaran = ws.cell(row=row_num, column=8, value=st.total_anggaran or 0)
        c_anggaran.number_format = '#,##0'
        
        c_cair = ws.cell(row=row_num, column=9, value=st.total_dicairkan or 0)
        c_cair.number_format = '#,##0'
        
        ws.cell(row=row_num, column=10, value=st.status_pencairan).alignment = Alignment(horizontal="center")
        ws.cell(row=row_num, column=11, value=st.status_lpj).alignment = Alignment(horizontal="center")

        for col_idx in range(1, 12):
            ws.cell(row=row_num, column=col_idx).border = border_thin

    # Set column widths
    for col_idx in range(1, 12):
        col_letter = get_column_letter(col_idx)
        max_len = 0
        for row in range(4, row_num + 1):
            val = ws.cell(row=row, column=col_idx).value
            if val:
                max_len = max(max_len, len(str(val)))
        ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    filename = f"Rekap_MONSIK_ST_SPD_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@export_bp.route('/excel/peserta')
@login_required
def excel_peserta():
    wb = Workbook()
    ws = wb.active
    ws.title = "Rekap Uang Harian & Pegawai"

    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="0A2540", end_color="0A2540", fill_type="solid")
    border_thin = Border(
        left=Side(style='thin', color='D0D5DD'),
        right=Side(style='thin', color='D0D5DD'),
        top=Side(style='thin', color='D0D5DD'),
        bottom=Side(style='thin', color='D0D5DD')
    )

    ws.merge_cells("A1:K1")
    ws["A1"] = "REKAPITULASI BIAYA PERJALANAN DINAS & UANG HARIAN PER PEGAWAI"
    ws["A1"].font = Font(name="Calibri", size=14, bold=True, color="0A2540")
    ws["A1"].alignment = Alignment(horizontal="center")

    headers = [
        "No", "Nomor ST", "Nama Pegawai", "NIP", "Jabatan / Gol",
        "Tujuan", "Jml Hari", "Uang Harian/Hari", "Total Uang Harian",
        "Transport & Hotel", "Total Diterima (Rp)"
    ]

    row_num = 3
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=row_num, column=col_num)
        cell.value = header
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = border_thin

    query = PesertaST.query.join(SuratTugas)
    if current_user.role == 'PEGAWAI':
        query = query.filter(
            (PesertaST.user_id == current_user.id) |
            (PesertaST.nip == current_user.nip) |
            (PesertaST.nama_pegawai == current_user.nama_lengkap)
        )
    peserta_list = query.order_by(SuratTugas.tanggal_st.desc()).all()
    for idx, p in enumerate(peserta_list, 1):
        row_num += 1
        ws.cell(row=row_num, column=1, value=idx).alignment = Alignment(horizontal="center")
        ws.cell(row=row_num, column=2, value=p.surat_tugas.nomor_st)
        ws.cell(row=row_num, column=3, value=p.nama_pegawai)
        ws.cell(row=row_num, column=4, value=p.nip or "-")
        ws.cell(row=row_num, column=5, value=f"{p.jabatan or '-'} ({p.golongan or '-'})")
        ws.cell(row=row_num, column=6, value=p.surat_tugas.kota_tujuan)
        ws.cell(row=row_num, column=7, value=p.jumlah_hari).alignment = Alignment(horizontal="center")
        
        c_uh = ws.cell(row=row_num, column=8, value=p.uang_harian_per_hari or 0)
        c_uh.number_format = '#,##0'
        
        c_tuh = ws.cell(row=row_num, column=9, value=p.total_uang_harian or 0)
        c_tuh.number_format = '#,##0'
        
        c_th = ws.cell(row=row_num, column=10, value=(p.biaya_transport or 0) + (p.biaya_penginapan or 0) + (p.biaya_lain or 0))
        c_th.number_format = '#,##0'
        
        c_tot = ws.cell(row=row_num, column=11, value=p.total_biaya_peserta or 0)
        c_tot.number_format = '#,##0'

        for col_idx in range(1, 12):
            ws.cell(row=row_num, column=col_idx).border = border_thin

    for col_idx in range(1, 12):
        col_letter = get_column_letter(col_idx)
        max_len = 0
        for row in range(3, row_num + 1):
            val = ws.cell(row=row, column=col_idx).value
            if val:
                max_len = max(max_len, len(str(val)))
        ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    filename = f"Rekap_MONSIK_Uang_Harian_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@export_bp.route('/cetak-spd/<int:st_id>')
@login_required
def cetak_spd(st_id):
    """Tampilan cetak standar format SPD / SIK siap print / simpan sebagai PDF via Browser Print"""
    st = SuratTugas.query.get_or_404(st_id)
    return render_template('export/cetak_spd.html', st=st, now=datetime.now())
