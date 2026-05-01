# 🔧 Setup Monitoring Apache2 Log Langsung

Dokumen ini menjelaskan bagaimana mengatur program untuk membaca langsung dari `/var/log/apache2/access.log`.

---

## 📌 Konfigurasi Program

Program telah diubah agar membaca dari **`/var/log/apache2/access.log`** secara langsung (bukan dari file lokal `access.log`).

**File yang dimodifikasi:**
- `main.py` → Konstanta `LOG_FILE` diubah ke `/var/log/apache2/access.log`
- `README.md` → Dokumentasi diperbarui

---

## ✅ Persyaratan

1. **Server Ubuntu/Linux dengan Apache2**
   ```bash
   sudo apt update
   sudo apt install apache2
   ```

2. **Python 3.10+** dan **pip**
   ```bash
   python3 --version
   pip3 --version
   ```

3. **Virtual Environment & Dependencies**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

---

## 🚀 Cara Menjalankan

### Opsi 1: Jalankan dengan Sudo (Paling Mudah)

```bash
# Dari folder project
sudo source venv/bin/activate  # Aktifkan venv dengan sudo
sudo python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
```

**Atau secara langsung:**
```bash
sudo /path/to/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
```

Dashboard akan accessible di: `http://localhost:8000`

---

### Opsi 2: Setup Permission User (Lebih Aman)

Alih-alih menjalankan dengan `sudo`, berikan user akses baca ke log Apache2:

```bash
# Tambahkan user ke group 'adm' (group yang bisa baca /var/log/)
sudo usermod -aG adm $USER

# Logout & login kembali agar perubahan aktif
logout
# atau gunakan:
newgrp adm
```

**Verifikasi akses:**
```bash
# Cek izin file
ls -la /var/log/apache2/access.log

# Coba baca isi
tail /var/log/apache2/access.log
```

Jika berhasil, jalankan program **tanpa sudo**:
```bash
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000
```

---

### Opsi 3: Setup Systemd Service (Production)

**1. Buat file service:**
```bash
sudo nano /etc/systemd/system/logmonitor.service
```

**2. Isi file dengan:**
```ini
[Unit]
Description=Log Monitor Dashboard - Apache2 Real-time
After=network.target apache2.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/home/user/ProjectUas
ExecStart=/home/user/ProjectUas/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=3
Environment="PATH=/home/user/ProjectUas/venv/bin"

[Install]
WantedBy=multi-user.target
```

**3. Reload & start service:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable logmonitor
sudo systemctl start logmonitor
sudo systemctl status logmonitor
```

**4. Monitor logs:**
```bash
sudo journalctl -u logmonitor -f
```

---

## 🧪 Test & Validasi

### 1. Pastikan Apache2 Berjalan

```bash
sudo systemctl status apache2
sudo systemctl start apache2  # Jika belum running
```

### 2. Generate Traffic ke Apache2

Buka terminal baru dan jalankan request:
```bash
# Request normal
curl http://localhost/
curl http://localhost/index.html

# Request yang terdeteksi sebagai attack (SQL injection)
curl "http://localhost/search?q=1' UNION SELECT"

# Request yang terdeteksi sebagai attack (XSS)
curl "http://localhost/?id=<script>alert(1)</script>"
```

### 3. Monitor Log File

Terminal lain:
```bash
# Real-time tail Apache2 log
tail -f /var/log/apache2/access.log
```

### 4. Check Dashboard

Buka browser: `http://localhost:8000`
- Setiap request ke Apache2 harus muncul di dashboard
- Status akan terklasifikasi sebagai "Normal" atau "Attack"

---

## ⚠️ Troubleshooting

### "Permission denied" saat membaca `/var/log/apache2/access.log`

**Solusi 1: Gunakan sudo**
```bash
sudo python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
```

**Solusi 2: Ubah ownership/permission log**
```bash
# Check izin current
ls -la /var/log/apache2/access.log

# Opsional: Ubah group (jangan ubah owner)
sudo chgrp adm /var/log/apache2/access.log
sudo chmod g+r /var/log/apache2/access.log
```

**Solusi 3: Jalankan sebagai user yang berbeda**
```bash
# Jalankan sebagai www-data user (user Apache2)
sudo -u www-data /home/user/ProjectUas/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
```

---

### Dashboard tidak menampilkan log baru

1. **Verifikasi file log ada & readable:**
   ```bash
   file /var/log/apache2/access.log
   cat /var/log/apache2/access.log | head -5
   ```

2. **Lihat logs program:**
   ```bash
   # Jika running di terminal, lihat error message
   # Jika running sebagai service:
   sudo journalctl -u logmonitor -n 50
   ```

3. **Generate traffic ke Apache2:**
   ```bash
   curl http://localhost/test
   ```

4. **Refresh dashboard di browser** (F5)

---

### Log rotation tidak terdeteksi

Program sudah handle log rotation otomatis. Jika masalah:
1. Restart program
2. Check `logrotate` config: `/etc/logrotate.d/apache2`

---

## 📝 File Penting

| File | Fungsi |
|------|--------|
| `main.py` | Backend dengan pembacaan log Apache2 |
| `index.html` | Frontend dashboard real-time |
| `requirements.txt` | Dependencies Python |
| `rf_model.pkl` | Model ML untuk klasifikasi |
| `tfidf.pkl` | Vectorizer untuk ekstraksi fitur |

---

## 🔗 Referensi

- Apache2 Log Format: [Apache Documentation](https://httpd.apache.org/docs/)
- FastAPI WebSocket: [FastAPI Docs](https://fastapi.tiangolo.com/advanced/websockets/)
- Systemd Services: [Systemd Manual](https://www.freedesktop.org/software/systemd/man/systemd.service.html)

---

**Dibuat: 2 Mei 2026**
**Diperbarui: Program konfigurasi untuk Apache2 real-time log**
