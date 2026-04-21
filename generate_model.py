"""
generate_model.py
─────────────────
Quick helper script to train a minimal Random Forest + TF-IDF model
and save the resulting .pkl artefacts for use by main.py.

Run once before starting the server:
    python generate_model.py

The training set covers common web-attack patterns (SQLi, XSS, path
traversal, command injection) as well as normal-looking URIs.
"""

import pickle
from pathlib import Path

from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

# ── Training Data ────────────────────────────────────────────────────────────
# 0 = Normal, 1 = Attack
SAMPLES = [
    # ---------- Normal traffic ----------
    ("/index.php", 0),
    ("/index.html", 0),
    ("/about", 0),
    ("/contact?name=John&email=john@mail.com", 0),
    ("/products?category=laptop&page=2", 0),
    ("/api/v1/users", 0),
    ("/api/v1/orders?status=pending", 0),
    ("/static/css/style.css", 0),
    ("/static/js/app.js", 0),
    ("/images/logo.png", 0),
    ("/login", 0),
    ("/logout", 0),
    ("/register", 0),
    ("/dashboard", 0),
    ("/search?q=python+tutorial", 0),
    ("/profile?id=42", 0),
    ("/favicon.ico", 0),
    ("/robots.txt", 0),
    ("/sitemap.xml", 0),
    ("/health", 0),
    ("/api/v2/products?limit=20&offset=0", 0),
    ("/blog/post/10", 0),
    ("/download/report.pdf", 0),
    ("/video/stream?id=99", 0),
    ("/cart?action=add&item=55", 0),

    # ---------- SQL Injection ----------
    ("/login?user=admin'--&pass=x", 1),
    ("/items?id=1 UNION SELECT null,table_name FROM information_schema.tables--", 1),
    ("/search?q=1' OR '1'='1", 1),
    ("/product?id=1; DROP TABLE users;--", 1),
    ("/page?id=1 AND 1=1--", 1),
    ("/user?id=1' AND SLEEP(5)--", 1),
    ("/api/data?filter=1%27%20OR%201%3D1--", 1),
    ("/report?id=1 UNION ALL SELECT NULL,NULL,NULL--", 1),
    ("/view?cat=1 ORDER BY 10--", 1),
    ("/items?id=1; INSERT INTO admin VALUES('hacker','pass')", 1),

    # ---------- Cross-Site Scripting (XSS) ----------
    ("/search?q=<script>alert('XSS')</script>", 1),
    ("/comment?text=<img src=x onerror=alert(1)>", 1),
    ("/name?value=<svg onload=alert(document.cookie)>", 1),
    ("/redirect?url=javascript:alert(1)", 1),
    ("/page?title=<body onresize=alert(1)>", 1),
    ("/input?data=%3Cscript%3Ealert%28XSS%29%3C%2Fscript%3E", 1),
    ("/profile?bio=<iframe src=evil.com>", 1),
    ("/msg?content=<marquee onstart=alert(1)>", 1),

    # ---------- Path Traversal / LFI ----------
    ("/download?file=../../etc/passwd", 1),
    ("/include?page=../../../etc/shadow", 1),
    ("/view?f=%2e%2e%2f%2e%2e%2fetc%2fpasswd", 1),
    ("/file?path=....//....//etc/passwd", 1),
    ("/img?src=/var/www/html/../../../etc/hosts", 1),
    ("/load?module=php://filter/convert.base64-encode/resource=index.php", 1),
    ("/open?resource=file:///etc/passwd", 1),

    # ---------- Command Injection ----------
    ("/ping?host=127.0.0.1;cat /etc/passwd", 1),
    ("/exec?cmd=ls+-la", 1),
    ("/tool?input=test|whoami", 1),
    ("/process?data=;id;", 1),
    ("/run?command=`uname -a`", 1),
    ("/check?ip=8.8.8.8%0Aid", 1),
    ("/api/exec?payload=$(cat /etc/shadow)", 1),

    # ---------- Common scanner / probing ----------
    ("/.env", 1),
    ("/wp-admin/", 1),
    ("/phpmyadmin/", 1),
    ("/admin/config.php", 1),
    ("/.git/config", 1),
    ("/shell.php", 1),
    ("/c99.php", 1),
    ("/xmlrpc.php", 1),
    ("/backup.zip", 1),
    ("/.DS_Store", 1),
]

payloads, labels = zip(*SAMPLES)

# ── Model Training ───────────────────────────────────────────────────────────
X_train, X_test, y_train, y_test = train_test_split(
    payloads, labels, test_size=0.2, random_state=42, stratify=labels
)

vectorizer = TfidfVectorizer(
    analyzer="char_wb",   # character n-grams are great for URI anomaly detection
    ngram_range=(2, 5),
    max_features=5000,
    sublinear_tf=True,
)

X_train_feat = vectorizer.fit_transform(X_train)
X_test_feat  = vectorizer.transform(X_test)

clf = RandomForestClassifier(
    n_estimators=200,
    max_depth=None,
    random_state=42,
    n_jobs=-1,
    class_weight="balanced",
)
clf.fit(X_train_feat, y_train)

# ── Evaluation ───────────────────────────────────────────────────────────────
y_pred = clf.predict(X_test_feat)
print("=" * 50)
print("Classification Report (test set)")
print("=" * 50)
print(classification_report(y_test, y_pred, target_names=["Normal", "Attack"]))

# ── Save Artefacts ───────────────────────────────────────────────────────────
with open("rf_model.pkl", "wb") as f:
    pickle.dump(clf, f)

with open("tfidf.pkl", "wb") as f:
    pickle.dump(vectorizer, f)

print("[OK] Saved: rf_model.pkl")
print("[OK] Saved: tfidf.pkl")
print()
print("You can now run:  uvicorn main:app --reload")
