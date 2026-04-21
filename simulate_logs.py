"""
simulate_logs.py
─────────────────
Injects realistic Apache Combined Log Format lines into access.log
to demo the real-time dashboard without a live web server.

Usage:
    python simulate_logs.py          # default: 1 log line every second
    python simulate_logs.py --delay 0.2
"""

import argparse
import random
import time
from datetime import datetime, timezone, timedelta

NORMAL_URIS = [
    "/",
    "/index.html",
    "/about",
    "/contact",
    "/products?category=electronics&page=1",
    "/api/v1/users",
    "/api/v1/orders?status=shipped",
    "/static/css/style.css",
    "/static/js/bundle.js",
    "/images/hero.png",
    "/login",
    "/dashboard",
    "/search?q=laptop+murah",
    "/profile?id=7",
    "/blog/post/12",
    "/cart?action=view",
    "/checkout",
    "/health",
    "/favicon.ico",
    "/robots.txt",
]

ATTACK_URIS = [
    "/login?user=admin'--&pass=x",
    "/items?id=1 UNION SELECT null,username,password FROM users--",
    "/search?q=<script>alert(document.cookie)</script>",
    "/download?file=../../etc/passwd",
    "/ping?host=127.0.0.1;id",
    "/.env",
    "/wp-admin/",
    "/shell.php?cmd=cat+/etc/shadow",
    "/page?id=1' AND SLEEP(5)--",
    "/view?img=<img src=x onerror=alert(1)>",
    "/include?page=../../../../etc/hosts",
    "/admin?pass=1' OR '1'='1",
    "/exec?cmd=ls+-la+-R+/",
    "/phpmyadmin/",
    "/.git/config",
    "/api/data?input=$(whoami)",
    "/upload?file=../../../var/www/html/shell.php",
    "/xmlrpc.php",
    "/backup.zip",
    "/c99.php",
]

IPS = [
    "192.168.1.10", "10.0.0.55", "172.16.0.22", "203.0.113.5",
    "198.51.100.11", "185.220.101.47", "91.108.4.200", "45.142.212.33",
    "192.168.10.105", "10.10.10.200",
]

STATUS_CODES = ["200", "200", "200", "301", "404", "403", "500"]
METHODS      = ["GET", "GET", "GET", "POST", "HEAD"]


def make_log_line(is_attack: bool) -> str:
    ip     = random.choice(IPS)
    method = random.choice(METHODS)
    uri    = random.choice(ATTACK_URIS if is_attack else NORMAL_URIS)
    status = random.choice(STATUS_CODES)
    size   = random.randint(200, 8192)

    tz_offset = timedelta(hours=7)
    now = datetime.now(tz=timezone(tz_offset))
    ts  = now.strftime("%d/%b/%Y:%H:%M:%S +0700")

    return f'{ip} - - [{ts}] "{method} {uri} HTTP/1.1" {status} {size}\n'


def main():
    parser = argparse.ArgumentParser(description="Simulate access.log entries")
    parser.add_argument("--delay", type=float, default=1.0,
                        help="Delay in seconds between entries (default: 1.0)")
    parser.add_argument("--attack-ratio", type=float, default=0.3,
                        help="Fraction of lines that are attacks (0–1, default: 0.3)")
    args = parser.parse_args()

    print(f"Writing to access.log every {args.delay}s  (attack ratio={args.attack_ratio:.0%})")
    print("Press Ctrl+C to stop.\n")

    with open("access.log", "a", encoding="utf-8") as f:
        try:
            while True:
                is_attack = random.random() < args.attack_ratio
                line = make_log_line(is_attack)
                f.write(line)
                f.flush()
                tag = "🔴 ATTACK" if is_attack else "🟢 Normal"
                print(f"{tag} → {line.strip()}")
                time.sleep(args.delay)
        except KeyboardInterrupt:
            print("\nSimulation stopped.")


if __name__ == "__main__":
    main()
