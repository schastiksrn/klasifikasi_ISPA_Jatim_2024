"""Buat Gambar 1 (diagram alir penelitian) untuk proposal.

Pakai:
    python scripts/buat_diagram_alir.py

Keluaran: output/figures/diagram_alir.png
"""

from pathlib import Path

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

OUT = Path("output/figures/diagram_alir.png")

WARNA = {
    "persiapan": "#cfe2f3",
    "data": "#d9ead3",
    "clustering": "#fce5cd",
    "klasifikasi": "#e4d7f5",
    "penutup": "#e8e8e8",
}

TAHAP = [
    ("1. Identifikasi Masalah", "rumusan masalah & tujuan", "persiapan"),
    ("2. Studi Literatur", "landasan teori & metode", "persiapan"),
    ("3. Pengumpulan Data", "38 kab/kota, Jawa Timur 2024", "data"),
    ("4. Pemeriksaan Kualitas", "duplikat, missing, nilai mustahil", "data"),
    ("5. Praproses Data", "rate, transformasi log, z-score", "data"),
    ("6. Eksplorasi Data", "deskriptif, histogram, korelasi", "data"),
    ("7. Clustering", "K-Means & Ward, k = 2..6", "clustering"),
    ("8. Validasi Cluster", "elbow, silhouette, dendrogram", "clustering"),
    ("9. Pelabelan", "rendah / sedang / tinggi", "clustering"),
    ("10. Klasifikasi Komparatif", "RF, LogReg, KNN, DT + baseline", "klasifikasi"),
    ("11. Evaluasi Model", "akurasi, F1, confusion matrix", "klasifikasi"),
    ("12. Interpretasi", "profil kategori & kesimpulan", "penutup"),
]

X_KIRI, X_KANAN = 0.27, 0.73
Y = [0.90, 0.765, 0.63, 0.495, 0.36, 0.225]
LEBAR, TINGGI = 0.40, 0.095


def kotak(ax, x, y, judul, sub, warna):
    ax.add_patch(FancyBboxPatch(
        (x - LEBAR / 2, y - TINGGI / 2), LEBAR, TINGGI,
        boxstyle="round,pad=0.012,rounding_size=0.02",
        linewidth=1.4, edgecolor="#5a5a5a", facecolor=warna, zorder=2,
    ))
    ax.text(x, y + 0.016, judul, ha="center", va="center",
            fontsize=13, fontweight="bold", zorder=3)
    ax.text(x, y - 0.020, sub, ha="center", va="center",
            fontsize=10, color="#444444", zorder=3)


def panah(ax, x1, y1, x2, y2):
    ax.add_patch(FancyArrowPatch(
        (x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=16,
        linewidth=1.6, color="#404040", shrinkA=0, shrinkB=0, zorder=1,
    ))


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(10, 11))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(0.5, 0.975, "Gambar 1. Diagram Alir Penelitian",
            ha="center", va="center", fontsize=17, fontweight="bold")

    # kolom kiri: 1-6 turun
    for i in range(6):
        j, s, w = TAHAP[i]
        kotak(ax, X_KIRI, Y[i], j, s, WARNA[w])

    # kolom kanan: 7-12 naik (dari bawah ke atas)
    kanan = TAHAP[6:]
    for i, (j, s, w) in enumerate(kanan):
        kotak(ax, X_KANAN, Y[5 - i], j, s, WARNA[w])

    # panah vertikal kolom kiri
    for i in range(5):
        panah(ax, X_KIRI, Y[i] - TINGGI / 2 - 0.012,
              X_KIRI, Y[i + 1] + TINGGI / 2 + 0.012)

    # panah 6 -> 7 (horizontal)
    panah(ax, X_KIRI + LEBAR / 2 + 0.012, Y[5],
          X_KANAN - LEBAR / 2 - 0.012, Y[5])

    # panah vertikal kolom kanan (naik)
    for i in range(5):
        panah(ax, X_KANAN, Y[5 - i] + TINGGI / 2 + 0.012,
              X_KANAN, Y[5 - i - 1] - TINGGI / 2 - 0.012)

    # legenda
    label = [("Persiapan", "persiapan"), ("Data", "data"),
             ("Clustering", "clustering"), ("Klasifikasi", "klasifikasi"),
             ("Penutup", "penutup")]
    xs = [0.13, 0.32, 0.51, 0.71, 0.89]
    for x, (teks, kunci) in zip(xs, label):
        ax.add_patch(mpatches.Rectangle((x - 0.035, 0.075), 0.030, 0.022,
                                        facecolor=WARNA[kunci], edgecolor="#5a5a5a",
                                        linewidth=1.1))
        ax.text(x + 0.002, 0.086, teks, ha="left", va="center", fontsize=11)

    ax.text(0.5, 0.035,
            "Inti pembentukan label: tahap 7-9  ->  masukan untuk tahap 10",
            ha="center", va="center", fontsize=11, style="italic", color="#444444")

    fig.savefig(OUT, dpi=200, bbox_inches="tight", facecolor="white")
    print("tersimpan:", OUT)


if __name__ == "__main__":
    main()
