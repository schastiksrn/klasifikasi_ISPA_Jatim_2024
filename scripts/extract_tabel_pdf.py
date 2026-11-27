"""Cari dan ekspor tabel dari PDF publikasi BPS / Profil Kesehatan.

Pakai:
    python scripts/extract_tabel_pdf.py "data/raw/Profil Kesehatan Jatim 2024.pdf"
    python scripts/extract_tabel_pdf.py "data/raw/xxx.pdf" --keyword sanitasi

Keluaran: output/extract/<namafile>_p<hal>_t<tabel>.csv + ringkasan di layar.
Tabel yang diekspor masih mentah; wajib dicek manual sebelum dipakai.
"""

import argparse
import re
import sys
from pathlib import Path

import pdfplumber

DEFAULT_KEYWORDS = [
    "ispa", "pneumonia", "sanitasi", "curah hujan", "kepadatan penduduk",
]

WILAYAH_RE = re.compile(r"(?i)kabupaten|kota")
KODE_RE = re.compile(r"^35\d{2}$")


def skor_tabel(tabel):
    """Tabel dianggap relevan bila banyak barisnya memuat nama/kode wilayah."""
    n = 0
    for baris in tabel:
        teks = " ".join(str(c) for c in baris if c is not None)
        if WILAYAH_RE.search(teks) or any(KODE_RE.match(str(c).strip()) for c in baris if c):
            n += 1
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf", help="path file PDF")
    ap.add_argument("--keyword", default=None,
                    help="kata kunci halaman, pisahkan dengan koma")
    ap.add_argument("--min-rows", type=int, default=8,
                    help="minimal baris agar tabel diekspor (default 8)")
    args = ap.parse_args()

    path = Path(args.pdf)
    if not path.exists():
        sys.exit(f"File tidak ditemukan: {path}")

    kws = ([k.strip().lower() for k in args.keyword.split(",")]
           if args.keyword else DEFAULT_KEYWORDS)

    outdir = Path("output/extract")
    outdir.mkdir(parents=True, exist_ok=True)
    stem = path.stem.replace(" ", "_")[:40]

    total_hal = 0
    total_tabel = 0
    total_ekspor = 0

    with pdfplumber.open(path) as pdf:
        total_hal = len(pdf.pages)
        print(f"file={path.name} | halaman={total_hal} | kata_kunci={kws}")

        for i, page in enumerate(pdf.pages, start=1):
            teks = (page.extract_text() or "").lower()
            kena = [k for k in kws if k in teks]
            if not kena:
                continue

            tabel_list = page.extract_tables()
            if not tabel_list:
                print(f"hal={i} | kena={kena} | tabel=0")
                continue

            for j, tabel in enumerate(tabel_list, start=1):
                total_tabel += 1
                n_baris = len(tabel)
                n_kol = max((len(r) for r in tabel), default=0)
                skor = skor_tabel(tabel)
                tanda = "EKSPOR" if (n_baris >= args.min_rows and skor >= args.min_rows // 2) else "lewati"
                print(f"hal={i} | tabel={j} | baris={n_baris} | kolom={n_kol} "
                      f"| baris_wilayah={skor} | {tanda} | kena={kena}")

                if tanda != "EKSPOR":
                    continue

                nama = outdir / f"{stem}_p{i}_t{j}.csv"
                with nama.open("w", newline="", encoding="utf-8") as f:
                    import csv
                    w = csv.writer(f)
                    for baris in tabel:
                        w.writerow(["" if c is None else str(c).replace("\n", " ").strip()
                                    for c in baris])
                total_ekspor += 1

    print(f"ringkasan: halaman={total_hal} | tabel_ditemukan={total_tabel} | diekspor={total_ekspor}")
    if total_ekspor:
        print(f"folder keluaran: {outdir.resolve()}")


if __name__ == "__main__":
    main()
