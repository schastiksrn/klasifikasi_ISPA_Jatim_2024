"""Uji coba pipeline: clustering -> label -> klasifikasi, memakai data yang sudah ada.

Data: IKU 2024, rate pneumonia 2025, sanitasi 2025.
Keluaran hanya untuk menguji kode, bukan hasil final.
"""

import warnings

import numpy as np
import pandas as pd
from sklearn.cluster import AgglomerativeClustering, KMeans
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import (accuracy_score, classification_report,
                             confusion_matrix, silhouette_score)
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")
RS = 42

iku = pd.read_csv("data/processed/iku_jatim_2024.csv", dtype={"kode_bps": str})
pneu = pd.read_csv("data/processed/pneumonia_2025.csv", dtype={"kode_bps": str})
san = pd.read_csv("data/processed/sanitasi_2025.csv", dtype={"kode_bps": str})

df = (iku[["kode_bps", "nama_wilayah", "jenis", "iku"]]
      .merge(pneu[["kode_bps", "rate_pneu", "prop_berat_pct"]], on="kode_bps")
      .merge(san[["kode_bps", "sanitasi"]], on="kode_bps"))

print(f"n={len(df)} | kolom kosong={int(df.isna().sum().sum())}")

# --- Blok A: pembentuk label ---
A = ["rate_pneu", "prop_berat_pct"]
Xa = StandardScaler().fit_transform(df[A].to_numpy(dtype="float64"))

print("\n== validasi jumlah cluster (blok A) ==")
print(f"{'k':>2} | {'KMeans':>8} | {'Ward':>8}")
for k in range(2, 7):
    km = KMeans(n_clusters=k, n_init=50, random_state=RS).fit(Xa)
    wd = AgglomerativeClustering(n_clusters=k, linkage="ward").fit(Xa)
    print(f"{k:>2} | {silhouette_score(Xa, km.labels_):>8.3f} | {silhouette_score(Xa, wd.labels_):>8.3f}")

# --- k = 3 sesuai kebutuhan kategori ---
km3 = KMeans(n_clusters=3, n_init=100, random_state=RS).fit(Xa)
wd3 = AgglomerativeClustering(n_clusters=3, linkage="ward").fit(Xa)
print(f"\nsilhouette k=3 | KMeans={silhouette_score(Xa, km3.labels_):.3f} "
      f"| Ward={silhouette_score(Xa, wd3.labels_):.3f}")

# --- urutkan cluster berdasarkan rata-rata rate_pneu -> rendah/sedang/tinggi ---
df["cluster"] = km3.labels_
urut = df.groupby("cluster")["rate_pneu"].mean().sort_values().index.tolist()
peta = {c: lab for c, lab in zip(urut, ["rendah", "sedang", "tinggi"])}
df["label"] = df["cluster"].map(peta)

print("\n== profil label ==")
print(df.groupby("label").agg(n=("kode_bps", "size"),
                              rate_pneu=("rate_pneu", "mean"),
                              prop_berat=("prop_berat_pct", "mean"),
                              iku=("iku", "mean"),
                              sanitasi=("sanitasi", "mean")).round(2).to_string())

# --- Blok B: klasifikasi ---
B = ["iku", "sanitasi"]
X = df[B].to_numpy(dtype="float64")
y = df["label"].to_numpy(dtype="object")

cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RS)
rf = RandomForestClassifier(n_estimators=300, max_depth=3, random_state=RS, class_weight="balanced")
pred = cross_val_predict(rf, X, y, cv=cv)

print("\n== klasifikasi (5-fold CV, fitur blok B) ==")
print(f"akurasi={accuracy_score(y, pred):.3f}")
print(classification_report(y, pred, zero_division=0, digits=3))
print("confusion matrix (baris=aktual, kolom=prediksi):")
print(pd.DataFrame(confusion_matrix(y, pred, labels=["rendah", "sedang", "tinggi"]),
                   index=["rendah", "sedang", "tinggi"],
                   columns=["rendah", "sedang", "tinggi"]).to_string())

rf.fit(X, y)
imp = permutation_importance(rf, X, y, n_repeats=100, random_state=RS)
print("\n== permutation importance ==")
for i, nama in enumerate(B):
    print(f"{nama:>10}: {imp.importances_mean[i]:+.3f} (sd {imp.importances_std[i]:.3f})")

df[["kode_bps", "nama_wilayah", "jenis", "cluster", "label"]].to_csv(
    "output/pilot_label.csv", index=False)
print("\ntersimpan: output/pilot_label.csv")
