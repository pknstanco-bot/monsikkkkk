# MONSIK – Sistem Monitoring SIK & SPD

MONSIK (Monitoring Surat Izin Kegiatan & Surat Perjalanan Dinas) adalah aplikasi web berbasis **Python Flask** dan **SQLite** yang dirancang khusus untuk memonitor, mengelola, dan mengarsipkan dokumen kegiatan penugasan dinas instansi/kantor.

Tampilan antarmuka mengadopsi tema modern executive dashboard (seperti pada PayTrack) dengan navbar warna Deep Navy, kartu metrik real-time, grafik tren penyerapan anggaran, dan manajemen dokumen DNPD.

---

## 1. Lingkungan & Teknologi

- **Operating System:** Windows 11
- **Backend:** Python 3.11 / Flask 3.0
- **Database:** SQLite (`instance/monsik.db`)
- **ORM:** SQLAlchemy (Flask-SQLAlchemy)
- **Autentikasi & Sesi:** Flask-Login
- **Frontend:** HTML5, CSS3, JavaScript (ES6), Bootstrap 5, Bootstrap Icons
- **Visualisasi Grafik:** Chart.js
- **Laporan & Export:** OpenPyXL (Excel), Format Cetak SPD Resmi

---

## 2. Struktur Direktori Proyek

```
C:\Monsik\
├── app/
│   ├── config.py             # Konfigurasi Development & Production
│   ├── models.py             # Model Database SQLAlchemy (User, ST, Peserta, Pencairan, Log)
│   ├── __init__.py           # Inisialisasi App Flask, Blueprints, Auto-seed DB
│   ├── routes/
│   │   ├── auth.py           # Login & Logout
│   │   ├── dashboard.py      # Metrik & API Chart.js
│   │   ├── surat_tugas.py    # CRUD ST & Multi-Peserta
│   │   ├── pencairan.py      # Outstanding vs Telah Cair, Pencatatan SP2D
│   │   ├── monitoring.py     # Monitoring Pegawai, Uang Harian, LPJ
│   │   ├── dnpd.py           # Upload, Download, Replace, Arsip DNPD
│   │   ├── export.py         # Export Excel & Cetak Format SPD
│   │   └── users.py          # Kelola Pengguna (Khusus Admin)
│   ├── static/
│   │   ├── css/monsik.css    # Gaya UI Modern Dark Navy Executive
│   │   └── js/monsik.js      # Script Kalkulasi Otomatis & Chart.js
│   └── templates/            # Template Jinja2 (Dashboard, ST, DNPD, dll)
├── instance/
│   └── monsik.db             # Database SQLite permanen
├── storage/
│   └── dnpd/                 # Penyimpanan permanen berkas DNPD
├── requirements.txt          # Daftar pustaka Python
├── setup.bat                 # Skrip instalasi dependensi & DB
├── START_MONSIK.bat          # Skrip sekali klik untuk menjalankan server
├── run.py                    # Titik masuk eksekusi Flask
└── README.md
```

---

## 3. Cara Menjalankan Server Lokal (Windows 11)

### Metode 1: Sekali Klik (Direkomendasikan)
Cukup klik ganda berkas:
```cmd
START_MONSIK.bat
```
Server akan mendeteksi environment dan menampilkan alamat lokal pada jendela terminal:
```
http://127.0.0.1:5000
```
Buka peramban (Google Chrome/Edge) dan masukkan alamat tersebut.

### Metode 2: Perintah Manual
Buka Command Prompt atau PowerShell di folder `C:\Monsik`:
```cmd
python run.py
```
atau menggunakan Python lokal:
```cmd
python\python.exe run.py
```

---

## 4. Akun Login Bawaan (Default Seed)

Saat pertama kali dijalankan, sistem otomatis membuat tabel database dan 3 akun demo dengan hak akses berbeda:

| Role | Username | Password | Deskripsi Wewenang |
| :--- | :--- | :--- | :--- |
| **ADMIN** | `admin` | `admin123` | Akses penuh, kelola pengguna, hapus Surat Tugas |
| **BENDAHARA** | `bendahara` | `bendahara123` | Proses pencairan dana, input SP2D, manajemen arsip DNPD |
| **PEGAWAI** | `budi` | `pegawai123` | Input ST, melihat riwayat penugasan, cetak format SPD |

---

## 5. Fitur Utama

1. **Dashboard Monitoring SIK & SPD:**
   - 5 Metrik Utama: Total Anggaran, Total Telah Cair, Outstanding (Belum Cair), Tingkat Realisasi (%), dan Total Personel.
   - Grafik Tren Volume Anggaran vs Pencairan (Chart.js Bar Chart).
   - Diagram Donut Komposisi Status Pencairan.
   - Status Progres Pertanggungjawaban (LPJ).
2. **Input Surat Tugas & Banyak Peserta (Multi-Peserta):**
   - Penambahan baris peserta secara dinamis tanpa batas dalam 1 ST.
   - Perhitungan otomatis Total Uang Harian (Tarif per hari × Durasi Hari Kalender).
   - Perhitungan otomatis Total Biaya Riil (Uang Harian + Transportasi + Penginapan).
3. **Pencairan SIK/SPD (Outstanding vs Cair):**
   - Pemisahan jelas pengajuan yang belum cair (Outstanding) dan yang sudah cair.
   - Pencairan fleksibel: Pencairan Penuh (100%), Uang Muka (Sebagian), atau Pelunasan.
   - Pencatatan nomor SP2D / Kwitansi / Bukti Bayar.
4. **Monitoring Pegawai & Uang Harian:**
   - Rekapitulasi frekuensi penugasan per pegawai.
   - Akumulasi total uang harian dan total biaya yang diterima oleh tiap personel.
5. **Manajemen Dokumen DNPD:**
   - Unggah berkas DNPD (PDF, Word, Excel, Gambar).
   - Penggantian (replace), preview langsung di browser, dan unduh berkas.
   - Semua berkas tersimpan permanen di `storage/dnpd/` (bukan folder sementara).
   - Menu khusus Arsip DNPD untuk memudahkan bendahara memeriksa kelengkapan SPJ.
6. **Ekspor Data & Cetak:**
   - Ekspor Rekapitulasi Surat Tugas ke format Microsoft Excel (.xlsx).
   - Ekspor Rekapitulasi Uang Harian per Pegawai ke Microsoft Excel (.xlsx).
   - Cetak langsung Format SPD Standar Kedinasan (siap cetak / simpan sebagai PDF).

---

## 6. Persiapan Pindah ke Server Kantor / Jaringan LAN

Aplikasi MONSIK telah didesain modular dan tidak melakukan *hardcode* alamat `127.0.0.1`.
Untuk mengaktifkan akses melalui jaringan LAN kantor:
1. Buka berkas `app/config.py` atau atur Environment Variable:
   ```cmd
   set FLASK_CONFIG=production
   set FLASK_HOST=0.0.0.0
   set FLASK_PORT=5000
   ```
2. Jalankan `run.py`. Aplikasi dapat diakses oleh komputer lain dalam satu jaringan WiFi/LAN kantor melalui:
   `http://<IP_KOMPUTER_SERVER>:5000`
