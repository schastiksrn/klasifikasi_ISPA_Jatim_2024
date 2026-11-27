"""Ekstrak Tabel 61 (pneumonia balita) dan Tabel 84 (sanitasi) dari Profil Kesehatan Jatim.

Pakai:
    python scripts/ekstrak_profil_kesehatan.py data/raw/<file>.pdf 2025

Keluaran di data/processed/:
    pneumonia_<tahun>.csv   -> rate penemuan pneumonia balita per 1.000 balita
    sanitasi_<tahun>.csv    -> persentase rumah tangga dengan akses sanitasi layak

Catatan: nomor halaman berbeda antar-edisi. Skrip mencari tabel berdasarkan
judul kolom, bukan nomor halaman.
"""

import re
import sys
from pathlib import Path

import pandas as pd
import pymupdf

DIM = Path("data/reference/dim_kabupaten_jatim.csv")


def angka(x):
    """Ubah '1.234,5' menjadi 1234.5; kosong/tanda hubung menjadi NaN."""
    if x is None:
        return float("nan")
    s = str(x).strip().replace(" ", "")
    if s in ("", "-", "nan", "None"):
        return float("nan")
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return float("nan")


def pecah_wilayah(label):
    """'KAB. PACITAN' -> ('Kabupaten', 'Pacitan'); 'KOTA BATU' -> ('Kota', 'Batu')."""
    s = str(label).strip()
    m = re.match(r"(?i)^(KAB\.?|KABUPATEN|KOTA)\s+(.*)$", s)
    if not m:
        return None, None
    jenis = "Kota" if m.group(1).upper().startswith("KOTA") else "Kabupaten"
    nama = m.group(2).strip().title()
    return jenis, nama


def cari_tabel(doc, penanda):
    """Kembalikan (nomor_halaman, daftar_baris) tabel pertama yang memuat penanda."""
    for i, page in enumerate(doc, start=1):
        teks = page.get_text()
        if not all(p in teks for p in penanda):
            continue
        tabs = page.find_tables()
        for t in tabs.tables:
            rows = t.extract()
            if len(rows) >= 30:
                return i, rows
    return None, None


def ambil_baris_wilayah(rows):
    out = []
    for r in rows:
        jenis, nama = pecah_wilayah(r[1]) if len(r) > 1 else (None, None)
        if jenis:
            out.append((jenis, nama, r))
    return out


def main():
    if len(sys.argv) < 3:
        sys.exit("pakai: ekstrak_profil_kesehatan.py <pdf> <tahun>")
    pdf_path, tahun = sys.argv[1], sys.argv[2]

    dim = pd.read_csv(DIM, dtype={"kode_bps": str})
    doc = pymupdf.open(pdf_path)

    # --- Tabel 61: pneumonia balita ---
    hal_p, rows_p = cari_tabel(doc, ["PNEUMONIA", "JUMLAH BALITA"])
    if rows_p is None:
        sys.exit("Tabel pneumonia tidak ditemukan")
    rec_p = []
    for jenis, nama, r in ambil_baris_wilayah(rows_p):
        rec_p.append({
            "jenis": jenis, "nama_wilayah": nama,
            "jumlah_balita": angka(r[3]),
            "perkiraan_pneumonia": angka(r[7]),
            "pneumonia_lp": angka(r[12]),
            "pneu_berat_lp": angka(r[13]),
            "total_penemuan": angka(r[14]),
            "cakupan_pct": angka(r[15]),
        })
    p = pd.DataFrame(rec_p)
    p["rate_pneu"] = (p["total_penemuan"] / p["jumlah_balita"] * 1000).round(2)
    p["rate_perkiraan"] = (p["perkiraan_pneumonia"] / p["jumlah_balita"] * 1000).round(2)
    p["prop_berat_pct"] = (p["pneu_berat_lp"] / p["total_penemuan"] * 100).round(2)

    # --- Tabel 84: sanitasi ---
    hal_s, rows_s = cari_tabel(doc, ["SANITASI", "JUMLAH KK"])
    if rows_s is None:
        sys.exit("Tabel sanitasi tidak ditemukan")
    rec_s = []
    for jenis, nama, r in ambil_baris_wilayah(rows_s):
        rec_s.append({
            "jenis": jenis, "nama_wilayah": nama,
            "jumlah_kk": angka(r[4]),
            "sanitasi": angka(r[8]),
            "sanitasi_aman_pct": angka(r[6]),
            "babs_terbuka_pct": angka(r[16]) if len(r) > 16 else float("nan"),
        })
    s = pd.DataFrame(rec_s)

    # --- join ke dimensi ---
    hasil = []
    for df, label in ((p, "pneumonia"), (s, "sanitasi")):
        m = dim.merge(df, on=["jenis", "nama_wilayah"], how="left", validate="one_to_one")
        # 'tahun' pada tabel dimensi adalah tahun acuan studi, bukan tahun terbit
        # publikasi. Ganti dengan tahun sumber yang sebenarnya agar tidak salah klaim.
        m = m.drop(columns=["tahun"], errors="ignore")
        m.insert(3, "tahun_sumber", int(tahun))
        print(f"{label}: sumber={len(df)} baris | hasil join={len(m)} | "
              f"tidak cocok={m.isna().sum().sum() - m['kode_bps'].isna().sum()}")
        hasil.append((label, m))

    outdir = Path("data/processed")
    outdir.mkdir(parents=True, exist_ok=True)

    pj = hasil[0][1]
    sj = hasil[1][1]
    pj.to_csv(outdir / f"pneumonia_{tahun}.csv", index=False)
    sj.to_csv(outdir / f"sanitasi_{tahun}.csv", index=False)

    print(f"tabel pneumonia: hal {hal_p} | tabel sanitasi: hal {hal_s}")
    print(f"rate_pneu: min={pj.rate_pneu.min():.2f} median={pj.rate_pneu.median():.2f} "
          f"max={pj.rate_pneu.max():.2f} | kosong={pj.rate_pneu.isna().sum()}")
    print(f"sanitasi : min={sj.sanitasi.min():.2f} median={sj.sanitasi.median():.2f} "
          f"max={sj.sanitasi.max():.2f} | kosong={sj.sanitasi.isna().sum()}")
    print("tersimpan:", outdir / f"pneumonia_{tahun}.csv", "|", outdir / f"sanitasi_{tahun}.csv")


if __name__ == "__main__":
    main()
