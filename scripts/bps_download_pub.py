"""Unduh publikasi BPS lewat API resmi, dengan verifikasi berkas.

Pakai:
    python scripts/bps_download_pub.py "Provinsi Jawa Timur Dalam Angka 2025" data/raw/jatim_dalam_angka_2025.pdf

Server BPS tidak mengirim Content-Length dan tidak mendukung Range, sehingga
unduhan bisa terputus tanpa error. Skrip ini memeriksa penanda %%EOF di akhir
berkas dan mengulang bila berkas tidak lengkap.
"""

import sys
import time
from pathlib import Path

import requests

BASE = "https://webapi.bps.go.id/v1/api"
DOMAIN = "3500"


def load_key():
    for line in Path(".env").read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("BPS_API_KEY="):
            return line.strip().split("=", 1)[1]
    sys.exit("BPS_API_KEY tidak ada di .env")


KEY = load_key()


def cari_terbitan(judul_target):
    r = requests.get(f"{BASE}/list/model/publication/domain/{DOMAIN}/key/{KEY}",
                     params={"keyword": judul_target}, timeout=40)
    d = r.json()
    if d.get("status") != "OK":
        sys.exit(f"API menolak: {d.get('message')}")
    items = d["data"][1]
    target = judul_target.lower().strip()
    for x in items:
        if x.get("title", "").lower().strip() == target:
            return x
    return items[0] if items else None


def pdf_lengkap(path):
    path = Path(path)
    if not path.exists() or path.stat().st_size < 1024:
        return False
    with path.open("rb") as f:
        f.seek(max(0, path.stat().st_size - 2048))
        ekor = f.read()
    return b"%%EOF" in ekor and b"%PDF" in path.open("rb").read(5)


def unduh_sekali(url, keluar):
    """Unduh sekali jalan. Server tidak mendukung Range, jadi tidak bisa resume."""
    n = 0
    berikutnya = 2 << 20
    t0 = time.time()
    headers = {"Accept-Encoding": "identity"}
    with requests.get(url, stream=True, timeout=(30, 900), headers=headers) as r:
        r.raise_for_status()
        with Path(keluar).open("wb") as f:
            for chunk in r.iter_content(1 << 16):
                f.write(chunk)
                n += len(chunk)
                if n >= berikutnya:
                    print(f"  {n/1e6:6.2f} MB | {time.time()-t0:6.1f} s", flush=True)
                    berikutnya += 2 << 20
    return n


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit('pakai: bps_download_pub.py "<judul>" <path_keluaran>')

    judul, keluar = sys.argv[1], sys.argv[2]
    pub = cari_terbitan(judul)
    if not pub:
        sys.exit("terbitan tidak ditemukan")
    print(f"ketemu: {pub['title']} | rilis={pub.get('rl_date')} | ukuran={pub.get('size')}", flush=True)

    for percobaan in range(1, 4):
        print(f"percobaan {percobaan}", flush=True)
        try:
            n = unduh_sekali(pub["pdf"], keluar)
        except Exception as e:
            print(f"  gagal: {type(e).__name__}", flush=True)
            time.sleep(5)
            continue
        ok = pdf_lengkap(keluar)
        print(f"  {n/1e6:.2f} MB | lengkap={ok}", flush=True)
        if ok:
            print("SELESAI", flush=True)
            break
        time.sleep(5)
    else:
        print("GAGAL: berkas tetap tidak lengkap setelah 3 percobaan", flush=True)
        sys.exit(1)
