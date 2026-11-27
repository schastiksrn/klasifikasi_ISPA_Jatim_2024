"""Tampilkan struktur data satu variabel BPS: tahun (turvar), wilayah (vervar), dan contoh nilai."""

import json
import sys
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


def detail(var_id):
    r = requests.get(f"{BASE}/list/model/data/domain/{DOMAIN}/var/{var_id}/key/{KEY}", timeout=60)
    d = r.json()
    print(f"\n===== var_id={var_id} | HTTP {r.status_code} | status={d.get('status')} =====")
    if d.get("status") != "OK":
        print(json.dumps(d)[:400])
        return None

    data = d["data"]
    print("kunci data:", list(data.keys()))

    if "var" in data:
        print("var:", [(x.get("val"), x.get("label")) for x in data["var"]])
    if "vervar" in data:
        vv = data["vervar"]
        print(f"vervar ({len(vv)}):", [(x.get("val"), x.get("label")) for x in vv][:6], "...")
    if "turvar" in data:
        tv = data["turvar"]
        print(f"turvar ({len(tv)}):", [(x.get("val"), x.get("label")) for x in tv][:20])
    if "tahun" in data:
        th = data["tahun"]
        print(f"tahun ({len(th)}):", [(x.get("val"), x.get("label")) for x in th])
    if "turtahun" in data:
        tt = data["turtahun"]
        print(f"turtahun ({len(tt)}):", [(x.get("val"), x.get("label")) for x in tt][:20])

    dc = data.get("datacontent", {})
    print("jumlah sel:", len(dc))
    for k, val in list(dc.items())[:8]:
        print(f"   key={k} -> {val}")
    return d


if __name__ == "__main__":
    for vid in sys.argv[1:]:
        detail(int(vid))
