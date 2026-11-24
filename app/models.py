from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    nama_lengkap = db.Column(db.String(128), nullable=False)
    nip = db.Column(db.String(32), unique=True, nullable=True)
    jabatan = db.Column(db.String(100), nullable=True)
    golongan = db.Column(db.String(20), nullable=True)
    role = db.Column(db.String(20), nullable=False, default='PEGAWAI')  # 'ADMIN', 'BENDAHARA', 'PEGAWAI'
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    created_st = db.relationship('SuratTugas', backref='pembuat', lazy=True, foreign_keys='SuratTugas.created_by_id')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == 'ADMIN'

    @property
    def is_bendahara(self):
        return self.role in ['ADMIN', 'BENDAHARA']


class SuratTugas(db.Model):
    __tablename__ = 'surat_tugas'

    id = db.Column(db.Integer, primary_key=True)
    nomor_st = db.Column(db.String(100), unique=True, nullable=False, index=True)
    nomor_spd = db.Column(db.String(100), nullable=True)
    tanggal_st = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    maksud_tugas = db.Column(db.Text, nullable=False)
    tempat_tujuan = db.Column(db.String(200), nullable=True, default='-')
    kota_tujuan = db.Column(db.String(100), nullable=True, default='-')
    
    tanggal_berangkat = db.Column(db.Date, nullable=True, default=datetime.utcnow)
    tanggal_kembali = db.Column(db.Date, nullable=True, default=datetime.utcnow)
    jumlah_hari = db.Column(db.Integer, nullable=False, default=1)
    
    tingkat_biaya = db.Column(db.String(50), default='Tingkat B')
    akun_anggaran = db.Column(db.String(100), default='524111 (Belanja Perjalanan Dinas Biasa)')
    
    # Jenis Surat: 'SIK' (Dalam Kota) atau 'SPD' (Luar Kota)
    jenis_surat = db.Column(db.String(20), default='SIK', nullable=False)
    
    # Status Progress: 'MERAH', 'KUNING', 'HIJAU'
    # MERAH: Belum Upload Laporan dan sinkron geotagging
    # KUNING: Sudah upload laporan menunggu pencairan
    # HIJAU: Telah cair
    progress_status = db.Column(db.String(50), default='MERAH', nullable=False)
    
    # Status SIK / SPD
    # Status Pencairan: 'OUTSTANDING' (Belum Cair), 'CAIR_SEBAGIAN', 'CAIR_PENUH'
    status_pencairan = db.Column(db.String(30), nullable=False, default='OUTSTANDING', index=True)
    
    # Status LPJ: 'BELUM_LPJ', 'MENUNGGU_VERIFIKASI', 'TERVERIFIKASI', 'SELESAI'
    status_lpj = db.Column(db.String(30), nullable=False, default='BELUM_LPJ', index=True)
    
    total_anggaran = db.Column(db.Float, default=0.0)
    total_dicairkan = db.Column(db.Float, default=0.0)
    
    # Dokumen DNPD (Daftar Nominatif Perjalanan Dinas)
    dnpd_filename = db.Column(db.String(255), nullable=True)
    dnpd_original_name = db.Column(db.String(255), nullable=True)
    dnpd_uploaded_at = db.Column(db.DateTime, nullable=True)
    dnpd_uploaded_by = db.Column(db.String(100), nullable=True)
    
    # Catatan tambahan
    catatan = db.Column(db.Text, nullable=True)
    
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    peserta_list = db.relationship('PesertaST', backref='surat_tugas', cascade='all, delete-orphan', lazy=True)
    pencairan_list = db.relationship('Pencairan', backref='surat_tugas', cascade='all, delete-orphan', lazy=True)

    def hitung_total_anggaran(self):
        total = sum(p.total_biaya_peserta for p in self.peserta_list)
        self.total_anggaran = total
        return total

    def update_status_pencairan(self):
        self.hitung_total_anggaran()
        if self.progress_status == 'HIJAU':
            self.total_dicairkan = self.total_anggaran
            self.status_pencairan = 'CAIR_PENUH'
            return

        total_cair = sum(c.jumlah_cair for c in self.pencairan_list)
        self.total_dicairkan = total_cair
        if total_cair <= 0:
            self.status_pencairan = 'OUTSTANDING'
        elif total_cair < self.total_anggaran:
            self.status_pencairan = 'CAIR_SEBAGIAN'
        else:
            self.status_pencairan = 'CAIR_PENUH'

    def get_peserta_for_user(self, user):
        if not user or not hasattr(user, 'is_authenticated') or not user.is_authenticated:
            return None
        for p in self.peserta_list:
            if p.user_id == user.id or (user.nip and p.nip == user.nip) or p.nama_pegawai == user.nama_lengkap:
                return p
        return None

    def get_anggaran_for_user(self, user):
        if user and getattr(user, 'role', '') == 'PEGAWAI':
            p = self.get_peserta_for_user(user)
            if p:
                return p.total_biaya_peserta or p.total_uang_harian or p.uang_harian_per_hari or 0.0
        return self.total_anggaran or 0.0

    def get_cair_for_user(self, user):
        if user and getattr(user, 'role', '') == 'PEGAWAI':
            p = self.get_peserta_for_user(user)
            if p:
                hak = p.total_biaya_peserta or p.total_uang_harian or p.uang_harian_per_hari or 0.0
                if self.progress_status == 'HIJAU' or self.status_pencairan == 'CAIR_PENUH':
                    return hak
                elif self.status_pencairan == 'OUTSTANDING':
                    return 0.0
                elif self.status_pencairan == 'CAIR_SEBAGIAN':
                    ratio = (self.total_dicairkan / self.total_anggaran) if (self.total_anggaran and self.total_anggaran > 0) else 0.0
                    return hak * min(1.0, max(0.0, ratio))
                return 0.0
        # Admin / Bendahara
        if self.progress_status == 'HIJAU':
            return self.total_anggaran or 0.0
        return self.total_dicairkan or 0.0

    def get_outstanding_for_user(self, user):
        if self.progress_status == 'HIJAU':
            return 0.0
        anggaran = self.get_anggaran_for_user(user)
        cair = self.get_cair_for_user(user)
        return max(0.0, anggaran - cair)

    @property
    def nominal_dicairkan(self):
        if self.progress_status == 'HIJAU':
            return self.total_anggaran or 0.0
        return self.total_dicairkan or 0.0

    @property
    def sisa_anggaran(self):
        if self.progress_status == 'HIJAU':
            return 0.0
        return max(0.0, (self.total_anggaran or 0.0) - (self.total_dicairkan or 0.0))

    @property
    def progress_info(self):
        if self.progress_status == 'HIJAU':
            return {
                'code': 'HIJAU',
                'color': 'success',
                'bg_class': 'bg-success',
                'text_class': 'text-success',
                'label': 'Telah cair',
                'icon': 'bi-check-circle-fill'
            }
        elif self.progress_status == 'KUNING':
            return {
                'code': 'KUNING',
                'color': 'warning',
                'bg_class': 'bg-warning text-dark',
                'text_class': 'text-warning',
                'label': 'Sudah upload laporan menunggu pencairan',
                'icon': 'bi-hourglass-split'
            }
        else:
            return {
                'code': 'MERAH',
                'color': 'danger',
                'bg_class': 'bg-danger',
                'text_class': 'text-danger',
                'label': 'Belum Upload Laporan dan sinkron geotagging',
                'icon': 'bi-exclamation-triangle-fill'
            }


class PesertaST(db.Model):
    __tablename__ = 'peserta_st'

    id = db.Column(db.Integer, primary_key=True)
    surat_tugas_id = db.Column(db.Integer, db.ForeignKey('surat_tugas.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    nama_pegawai = db.Column(db.String(128), nullable=False)
    nip = db.Column(db.String(32), nullable=True)
    golongan = db.Column(db.String(20), nullable=True)
    jabatan = db.Column(db.String(100), nullable=True)
    peran = db.Column(db.String(50), default='Anggota') # Ketua Tim / Anggota / Pengemudi
    
    # Komponen Biaya Perjalanan Dinas
    uang_harian_per_hari = db.Column(db.Float, default=430000.0) # SBU standar per hari
    jumlah_hari = db.Column(db.Integer, default=1)
    total_uang_harian = db.Column(db.Float, default=0.0)
    
    biaya_transport = db.Column(db.Float, default=0.0) # Tiket pesawat / kereta / bbm / tol
    biaya_penginapan = db.Column(db.Float, default=0.0) # Hotel / wisma
    biaya_lain = db.Column(db.Float, default=0.0) # Representasi / sewa kendaraan lokal
    total_biaya_peserta = db.Column(db.Float, default=0.0)
    
    status_lpj_peserta = db.Column(db.String(30), default='BELUM_LPJ')
    keterangan = db.Column(db.String(255), nullable=True)

    # Relationship to user if linked
    user = db.relationship('User', backref='riwayat_st', foreign_keys=[user_id])

    def hitung_total(self):
        # Uang harian langsung berupa nominal angka riil tanpa dikalikan jumlah hari
        if self.total_uang_harian is None or self.total_uang_harian == 0:
            self.total_uang_harian = (self.uang_harian_per_hari or 0.0)
        self.total_biaya_peserta = (
            (self.total_uang_harian or 0.0) +
            (self.biaya_transport or 0.0) +
            (self.biaya_penginapan or 0.0) +
            (self.biaya_lain or 0.0)
        )
        return self.total_biaya_peserta


class Pencairan(db.Model):
    __tablename__ = 'pencairan'

    id = db.Column(db.Integer, primary_key=True)
    surat_tugas_id = db.Column(db.Integer, db.ForeignKey('surat_tugas.id'), nullable=False)
    nomor_sp2d_kwitansi = db.Column(db.String(100), nullable=False)
    tanggal_cair = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    jumlah_cair = db.Column(db.Float, nullable=False)
    jenis_pencairan = db.Column(db.String(30), default='PENUH')  # 'UANG_MUKA', 'PELUNASAN', 'PENUH'
    metode_bayar = db.Column(db.String(50), default='Transfer Bank') # 'Transfer Bank', 'Tunai'
    catatan = db.Column(db.Text, nullable=True)
    
    bendahara_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    bendahara = db.relationship('User', foreign_keys=[bendahara_id])


class LogAktivitas(db.Model):
    __tablename__ = 'log_aktivitas'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    username = db.Column(db.String(64), nullable=True)
    aktivitas = db.Column(db.String(255), nullable=False)
    modul = db.Column(db.String(50), nullable=False)
    detail = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
