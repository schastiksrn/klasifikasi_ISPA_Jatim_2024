"""Pipeline final: clustering (K-Means vs Ward) lalu klasifikasi (Random Forest).

Pakai:
    python scripts/pipeline_final.py

Masukan : data/processed/dataset_final_2024.csv  (38 baris x 5 variabel)
Keluaran: output/cluster_labels_2024.csv, output/pipeline_summary.txt
"""

import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import AgglomerativeClustering, KMeans
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, adjusted_rand_score, classification_report,
                             f1_score, silhouette_score)
from sklearn.model_selection import LeaveOneOut, cross_val_predict
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

warnings.filterwarnings("ignore")

DATA = Path("data/processed/dataset_final_2024.csv")
OUT = Path("output")

BLOK_A = ["rate_pneu", "prop_berat_pct"]   # pembentuk label
BLOK_B = ["iku", "sanitasi", "kepadatan"]  # prediktor klasifikasi


def siapkan():
    df = pd.read_csv(DATA, dtype={"kode_bps": str})
    X = df[BLOK_A].copy()
    # log untuk variabel dengan kemencengan positif > 1 (sesuai F.2.6)
    for c in BLOK_A:
        if X[c].skew() > 1:
            X[c] = np.log1p(X[c])
    Z = StandardScaler().fit_transform(X)
    return df, Z


def uji_k(Z, k_range=range(2, 7)):
    baris = []
    for k in k_range:
        km = KMeans(n_clusters=k, n_init=50, random_state=42).fit(Z)
        wd = AgglomerativeClustering(n_clusters=k, linkage="ward").fit(Z)
        baris.append({
            "k": k,
            "kmeans": silhouette_score(Z, km.labels_),
            "ward": silhouette_score(Z, wd.labels_),
        })
    return pd.DataFrame(baris)


def label_urut(df, labels):
    """Beri nama rendah/sedang/tinggi berdasarkan rata-rata rate_pneu."""
    s = pd.Series(labels, index=df.index)
    urut = df.groupby(s)["rate_pneu"].mean().sort_values().index.tolist()
    nama = {c: n for c, n in zip(urut, ["rendah", "sedang", "tinggi"])}
    return s.map(nama)


def stabilitas(Z, k, acuan, n=50):
    """Seberapa sering label sama muncul ulang dengan seed berbeda."""
    skor = []
    for seed in range(n):
        lab = KMeans(n_clusters=k, n_init=10, random_state=seed).fit_predict(Z)
        skor.append(adjusted_rand_score(acuan, lab))
    return float(np.mean(skor)), float(np.min(skor))


def main():
    OUT.mkdir(exist_ok=True)
    df, Z = siapkan()

    print("=" * 62)
    print("1. VALIDASI CLUSTER (silhouette, data 2024, blok A)")
    print("=" * 62)
    tab = uji_k(Z)
    print(tab.round(3).to_string(index=False))
    print("\nCatatan: k=3 diwajibkan oleh kebutuhan kategori rendah/sedang/tinggi.")

    # metode terbaik pada k=3
    skor3 = tab[tab.k == 3].iloc[0]
    metode = "kmeans" if skor3.kmeans >= skor3.ward else "ward"
    print(f"\nMetode terbaik pada k=3: {metode.upper()} "
          f"(silhouette {max(skor3.kmeans, skor3.ward):.3f})")

    if metode == "kmeans":
        lab = KMeans(n_clusters=3, n_init=50, random_state=42).fit_predict(Z)
    else:
        lab = AgglomerativeClustering(n_clusters=3, linkage="ward").fit_predict(Z)

    df["label"] = label_urut(df, lab)

    print("\n" + "=" * 62)
    print("2. PROFIL TIAP KATEGORI")
    print("=" * 62)
    profil = df.groupby("label")[BLOK_A + BLOK_B].agg(["mean", "count"])
    ringkas = df.groupby("label").agg(
        n=("kode_bps", "size"),
        rate_pneu=("rate_pneu", "mean"),
        prop_berat=("prop_berat_pct", "mean"),
        iku=("iku", "mean"),
        sanitasi=("sanitasi", "mean"),
        kepadatan=("kepadatan", "mean"),
    ).reindex(["rendah", "sedang", "tinggi"])
    print(ringkas.round(2).to_string())

    print("\n" + "=" * 62)
    print("3. UJI STABILITAS (50 seed berbeda, ARI terhadap label utama)")
    print("=" * 62)
    rata, minimum = stabilitas(Z, 3, lab)
    print(f"ARI rata-rata = {rata:.3f} | terendah = {minimum:.3f}")
    print("(ARI 1,0 = identik; > 0,8 = sangat stabil)")

    print("\n" + "=" * 62)
    print("4. KLASIFIKASI (LOOCV, n=38, fitur blok B)")
    print("=" * 62)
    Xb = df[BLOK_B].to_numpy(float)
    y = df["label"].to_numpy(object)
    loo = LeaveOneOut()
    model = {
        "Random Forest": RandomForestClassifier(n_estimators=500, max_depth=3,
                                                random_state=42),
        "LogReg": make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000)),
        "KNN-5": make_pipeline(StandardScaler(), KNeighborsClassifier(5)),
        "Tree-d3": DecisionTreeClassifier(max_depth=3, random_state=42),
    }
    hasil = []
    for nama, m in model.items():
        pr = cross_val_predict(m, Xb, y, cv=loo)
        hasil.append({"model": nama,
                      "akurasi": accuracy_score(y, pr),
                      "macroF1": f1_score(y, pr, average="macro")})
    print(pd.DataFrame(hasil).round(3).to_string(index=False))
    print(f"\nTebak acak 3 kelas = {1/3:.3f}")

    rf = RandomForestClassifier(n_estimators=500, max_depth=3, random_state=42).fit(Xb, y)
    print("\nFeature importance (RF, seluruh data):")
    for c, v in sorted(zip(BLOK_B, rf.feature_importances_), key=lambda t: -t[1]):
        print(f"  {c:12} {v:.3f}")

    pr = cross_val_predict(rf, Xb, y, cv=loo)
    print("\nLaporan per kelas (RF, LOOCV):")
    print(classification_report(y, pr, zero_division=0))

    dim = pd.read_csv("data/reference/dim_kabupaten_jatim.csv", dtype={"kode_bps": str})
    keluaran = dim.merge(
        df[["kode_bps", "label"] + BLOK_A + BLOK_B], on="kode_bps", how="left"
    )
    keluaran.to_csv(OUT / "cluster_labels_2024.csv", index=False)
    print("tersimpan:", OUT / "cluster_labels_2024.csv")


if __name__ == "__main__":
    main()
