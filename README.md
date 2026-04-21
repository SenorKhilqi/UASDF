# 🛡️ Real-Time Log Monitoring Dashboard

> Sistem monitoring log server berbasis web secara real-time dengan deteksi serangan menggunakan Machine Learning (Random Forest + TF-IDF).

---

## 📋 Deskripsi

Dashboard ini memantau file `access.log` (format Apache/Nginx Combined Log) secara real-time dan mengklasifikasikan setiap request HTTP sebagai **Normal** atau **Attack** menggunakan model Machine Learning yang telah dilatih sebelumnya. Hasil klasifikasi langsung ditampilkan di browser melalui **WebSocket**.

### Jenis Serangan yang Dideteksi:
- 💉 **SQL Injection** (SQLi)
- 🕸️ **Cross-Site Scripting** (XSS)
- 📁 **Path Traversal / Local File Inclusion** (LFI)
- ⚙️ **Command Injection**
- 🔍 **Common Scanner & Web Probing** (`.env`, `wp-admin`, `phpMyAdmin`, dll.)

---

## 🗂️ Struktur Project

```
ProjectUas/
├── main.py              # Backend FastAPI + WebSocket + log tailer
├── index.html           # Frontend dashboard (dark mode, real-time)
├── generate_model.py    # Script untuk melatih & menyimpan model ML
├── simulate_logs.py     # Script simulasi log untuk demo/testing
├── requirements.txt     # Daftar dependensi Python
├── rf_model.pkl         # Model Random Forest (hasil generate_model.py)
├── tfidf.pkl            # TF-IDF Vectorizer (hasil generate_model.py)
└── access.log           # File log yang dimonitor (dibuat otomatis)
```

---

## ⚙️ Teknologi

| Layer | Teknologi |
|-------|-----------|
| Backend | FastAPI, Uvicorn |
| Real-time | WebSocket |
| Machine Learning | Scikit-learn (Random Forest + TF-IDF) |
| Frontend | HTML, CSS, Vanilla JavaScript |
| Log Format | Apache/Nginx Combined Log Format |

---

## 🚀 Cara Menjalankan (Lokal / Windows)

### 1. Clone atau Download Project

```bash
git clone https://github.com/username/ProjectUas.git
cd ProjectUas
```

### 2. Buat Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate
```

### 3. Install Dependensi

```bash
pip install -r requirements.txt
```

### 4. (Opsional) Generate Ulang Model ML

> Lewati langkah ini jika `rf_model.pkl` dan `tfidf.pkl` sudah tersedia.

```bash
python generate_model.py
```

Output yang diharapkan:
```
==================================================
Classification Report (test set)
==================================================
              precision    recall  f1-score ...
...
[OK] Saved: rf_model.pkl
[OK] Saved: tfidf.pkl
```

### 5. Jalankan Server

```bash
uvicorn main:app --reload
```

### 6. Buka Dashboard

Akses di browser: **http://localhost:8000**

---

## 🧪 Simulasi Log (Demo)

Untuk mensimulasikan traffic log tanpa server Nginx/Apache nyata, buka **terminal baru** dan jalankan:

```bash
# Default: 1 log per detik, 30% attack ratio
python simulate_logs.py

# Custom: lebih cepat & lebih banyak serangan
python simulate_logs.py --delay 0.2 --attack-ratio 0.5
```

| Argumen | Default | Keterangan |
|---------|---------|------------|
| `--delay` | `1.0` | Jeda (detik) antar baris log |
| `--attack-ratio` | `0.3` | Proporsi log serangan (0.0–1.0) |

Dashboard akan langsung memperbarui tampilan secara real-time.

---

## 🔌 API Endpoints

| Method | Endpoint | Keterangan |
|--------|----------|------------|
| `GET` | `/` | Halaman dashboard utama |
| `GET` | `/health` | Status server & model |
| `WebSocket` | `/ws` | Stream log real-time |

### Contoh Response `/health`:
```json
{
  "status": "ok",
  "model_loaded": true,
  "clients_connected": 1,
  "log_file": "access.log",
  "log_exists": true
}
```

---

## 🖥️ Deploy ke Ubuntu Server

### Persyaratan Server
- Ubuntu 20.04 / 22.04
- Python 3.10+
- Nginx (opsional, sebagai reverse proxy)

### Langkah Cepat

**1. Transfer file ke server:**
```bash
scp -r ./ProjectUas user@IP_SERVER:/home/user/
```

**2. Setup di server:**
```bash
cd /home/user/ProjectUas
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**3. Jalankan:**
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Akses dashboard: `http://IP_SERVER:8000`

### Setup Auto-Start dengan Systemd

Buat file service:
```bash
sudo nano /etc/systemd/system/logmonitor.service
```

Isi:
```ini
[Unit]
Description=Log Monitor Dashboard - FastAPI
After=network.target

[Service]
Type=simple
User=user
WorkingDirectory=/home/user/ProjectUas
ExecStart=/home/user/ProjectUas/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Aktifkan:
```bash
sudo systemctl daemon-reload
sudo systemctl enable logmonitor
sudo systemctl start logmonitor
sudo systemctl status logmonitor
```

### Integrasi Log Nginx/Apache Asli

```bash
# Symlink ke log Nginx asli
ln -s /var/log/nginx/access.log /home/user/ProjectUas/access.log
```

> Pastikan user punya izin baca log: `sudo usermod -aG adm user`

### Konfigurasi Nginx (Reverse Proxy + WebSocket)

```nginx
server {
    listen 80;
    server_name IP_SERVER;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 3600s;
    }
}
```

---

## 🤖 Detail Model Machine Learning

| Parameter | Nilai |
|-----------|-------|
| Algoritma | Random Forest |
| Vectorizer | TF-IDF (character n-gram, 2–5) |
| Max Features | 5.000 |
| N Estimators | 200 |
| Class Weight | Balanced |
| Training Samples | ~65 baris (Normal + Attack) |

### Fallback Mode
Jika file `.pkl` tidak ditemukan, sistem secara otomatis beralih ke **mode heuristic** yang mendeteksi serangan berdasarkan keyword umum (`SELECT`, `UNION`, `<script>`, `../`, `eval(`, dll.).

---

## 🛠️ Troubleshooting

| Masalah | Solusi |
|---------|--------|
| Port 8000 tidak bisa diakses | Cek firewall: `sudo ufw allow 8000/tcp` |
| WebSocket tidak connect di balik Nginx | Pastikan header `Upgrade` ada di config Nginx |
| `rf_model.pkl` tidak ditemukan | Jalankan `python generate_model.py` terlebih dahulu |
| Permission denied pada `access.log` | `sudo usermod -aG adm $USER` lalu re-login |
| Service tidak start | Cek log: `sudo journalctl -u logmonitor -n 50` |

---

## 📦 Requirements

```
fastapi==0.111.0
uvicorn[standard]==0.29.0
websockets==12.0
scikit-learn==1.4.2
numpy==1.26.4
python-multipart==0.0.9
aiofiles==23.2.1
```

---

## 📄 Lisensi

Project ini dibuat untuk keperluan **tugas akhir mata kuliah Digital Forensics / Ethical Hacking**.

---

*Built with ❤️ using FastAPI, Scikit-learn, and WebSocket*
