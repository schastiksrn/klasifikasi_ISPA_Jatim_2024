"""Cari variabel BPS yang relevan untuk domain Jawa Timur (3500).

API key dibaca dari .env dan tidak pernah ditampilkan.
"""

import json
import sys
from pathlib import Path

import requests

BASE = "https://webapi.bps.go.id/v1/api"
DOMAIN = "3500"
KATA = ("hujan", "kepadatan", "sanitasi", "ispa", "udara", "pneumonia", "penduduk")


def load_key():
    for line in Path(".env").read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("BPS_API_KEY="):
            return line.strip().split("=", 1)[1]
    sys.exit("BPS_API_KEY tidak ada di .env")


KEY = load_key()


def ambil(path):
    r = requests.get(f"{BASE}/{path}", timeout=30)
    if r.status_code != 200:
        return None
    d = r.json()
    if d.get("status") != "OK":
        return None
    return d["data"]


def semua_var():
    hasil = []
    page, pages = 1, 1
    while page <= pages:
        data = ambil(f"list/model/var/domain/{DOMAIN}/page/{page}/key/{KEY}")
        if data is None:
            print(f"  halaman {page}: gagal")
            break
        meta, items = data[0], data[1]
        pages = meta["pages"]
        hasil.extend(items)
        page += 1
    return hasil


if __name__ == "__main__":
    v = semua_var()
    print(f"total variabel domain {DOMAIN}: {len(v)}")

    cocok = [x for x in v if any(k in (x.get("title") or "").lower() for k in KATA)]
    print(f"kandidat: {len(cocok)}\n")
    for x in cocok:
        print(f"var_id={x['var_id']:<5} | {x['title'][:70]:<70} | unit={x.get('unit')}")
