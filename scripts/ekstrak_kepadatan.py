"""Ekstrak Tabel 3.1.1 (kepadatan penduduk per kabupaten/kota) dari Dalam Angka.

Pakai:
    python scripts/ekstrak_kepadatan.py data/raw/jatim_dalam_angka_2025.pdf 2024

Keluaran: data/processed/kepadatan_<tahun>.csv

Catatan: tabel memuat tiga kolom tahun (2020, 2024, 2025). Skrip mengambil kolom
sesuai argumen tahun. Baris penanda "Kabupaten/Regency" dan "Kota/Municipality"
dipakai untuk membedakan Kabupaten Blitar dan Kota Blitar.
"""

import re
import sys
from pathlib import Path

import pandas as pd
import pymupdf

DIM = Path("data/reference/dim_kabupaten_jatim.csv")


def bersih_angka(x):
    """'d\\ni\\n1.109' -> 1109. Buang sisa teks watermark, lalu titik ribuan."""
    if x is None:
        return None
    s = re.sub(r"[^0-9.]", "", str(x))
    if not s or s == ".":
        return None
    return int(s.replace(".", ""))


def bersih_nama(x):
    """'s\\nMagetan' -> 'Magetan'; 'Pacitan' -> 'Pacitan'."""
    if x is None:
        return None
    bagian = [b.strip() for b in str(x).split("\n") if b.strip()]
    if not bagian:
        return None
    return bagian[-1].title()


def cari_tabel(doc, penanda):
    """Cari tabel yang judul kolomnya benar-benar 'Kepadatan Penduduk'.

    Halaman 123 juga memuat frasa 'Kepadatan Penduduk' pada judul tabel, tetapi
    isinya jumlah penduduk (jiwa). Karena itu header tabel ikut diperiksa.
    """
    for i, page in enumerate(doc, start=1):
        teks = page.get_text()
        if not all(p in teks for p in penanda):
            continue
        for t in page.find_tables().tables:
            rows = t.extract()
            if len(rows) < 35:
                continue
            header = " ".join(str(c) for c in rows[0] if c).lower()
            if "kepadatan" not in header:
                continue
            return i, rows
    return None, None


def main():
    if len(sys.argv) < 3:
        sys.exit("pakai: ekstrak_kepadatan.py <pdf> <tahun>")
    pdf_path, tahun = sys.argv[1], int(sys.argv[2])

    doc = pymupdf.open(pdf_path)
    hal, rows = cari_tabel(doc, ["Kepadatan Penduduk", "Kabupaten/Kota"])
    if rows is None:
        sys.exit("Tabel kepadatan tidak ditemukan")

    # kolom: 1 nama, 2 = 2020, 3 = 2024, 4 = 2025
    kolom = {2020: 1, 2024: 2, 2025: 3}.get(tahun)
    if kolom is None:
        sys.exit(f"tahun {tahun} tidak tersedia pada tabel (hanya 2020, 2024, 2025)")

    jenis = None
    rec = []
    for r in rows:
        sel0 = str(r[0]).lower() if r[0] else ""
        if "kabupaten/regency" in sel0:
            jenis = "Kabupaten"
            continue
        if "kota/municipality" in sel0:
            jenis = "Kota"
            continue
        if "jawa timur" in sel0:
            break
        if jenis is None:
            continue
        nilai = bersih_angka(r[kolom])
        nama = bersih_nama(r[0])
        if nama and nilai is not None:
            rec.append({"jenis": jenis, "nama_wilayah": nama, "kepadatan": nilai})

    df = pd.DataFrame(rec)
    dim = pd.read_csv(DIM, dtype={"kode_bps": str})
    m = dim[["kode_bps", "nama_wilayah", "jenis"]].merge(
        df, on=["jenis", "nama_wilayah"], how="left", validate="one_to_one"
    )
    m.insert(3, "tahun_sumber", tahun)

    print(f"tabel: hal {hal} | baris terbaca={len(df)} | hasil join={len(m)} | "
          f"kosong={m.kepadatan.isna().sum()}")
    print(f"kepadatan: min={m.kepadatan.min():.0f} median={m.kepadatan.median():.0f} "
          f"max={m.kepadatan.max():.0f}")

    out = Path("data/processed") / f"kepadatan_{tahun}.csv"
    m.to_csv(out, index=False)
    print("tersimpan:", out)
    print(m.nlargest(3, "kepadatan")[["kode_bps", "nama_wilayah", "jenis", "kepadatan"]].to_string(index=False))
    print(m.nsmallest(3, "kepadatan")[["kode_bps", "nama_wilayah", "jenis", "kepadatan"]].to_string(index=False))


if __name__ == "__main__":
    main()
