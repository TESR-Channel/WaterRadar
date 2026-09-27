#!/usr/bin/env python3
"""ดึงข้อมูลน้ำจาก ThaiWater (สสน.) เฉพาะรอบบ้าน แล้วเขียน data/latest.json + data/history.json
ใช้แค่ standard library — ไม่ต้อง pip install"""
import json, math, os, time, urllib.request
from datetime import datetime, timedelta, timezone

BASE = "https://api-v3.thaiwater.net/api/v1/thaiwater30"
LAT = float(os.getenv("HOME_LAT", "13.8600"))
LNG = float(os.getenv("HOME_LNG", "100.4800"))
RADIUS = float(os.getenv("RADIUS_KM", "30"))
HISTORY_DAYS = float(os.getenv("HISTORY_DAYS", "3"))
SOURCES = {
    "waterlevel": "/public/waterlevel_load",
    "canal": "/public/canal_waterlevel",
    "rain": "/public/rain_24h",
    "flood_road": "/public/flood_road",
    "cctv": "/analyst/cctv",
}
HEADERS = {
    "User-Agent": "Mozilla/5.0 (TESR WaterRadar; +https://github.com/TESR-Channel/WaterRadar)",
    "Referer": "https://www.thaiwater.net/",
    "Accept": "application/json",
}
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
now = datetime.now(timezone.utc)
iso = lambda d: d.strftime("%Y-%m-%dT%H:%M:%SZ")


def get(path):
    err = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(BASE + path, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception as e:  # noqa: BLE001
            err = e
            time.sleep(5 * (attempt + 1))
    raise err


def num(v):
    try:
        f = float(v)
        return f if math.isfinite(f) else None
    except (TypeError, ValueError):
        return None


def coords(o):
    """หา lat/lng จากตัว record หรือ dict ย่อย (station, canal_station, ...)"""
    for d in [o] + [v for v in o.values() if isinstance(v, dict)]:
        lat = next((num(v) for k, v in d.items() if "lat" in k.lower() and num(v)), None)
        lng = next((num(v) for k, v in d.items() if any(s in k.lower() for s in ("lon", "lng")) and num(v)), None)
        if lat and lng:
            return lat, lng
    return None


def km(a, b, c, d):
    r = math.radians
    h = math.sin(r(c - a) / 2) ** 2 + math.cos(r(a)) * math.cos(r(c)) * math.sin(r(d - b) / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


def nearby(obj):
    """เดินทั้ง JSON เก็บ record ที่มีพิกัดและอยู่ในรัศมี"""
    out = []
    if isinstance(obj, list):
        if obj and all(isinstance(x, dict) for x in obj) and any(coords(x) for x in obj[:20]):
            for x in obj:
                c = coords(x)
                if c and km(LAT, LNG, *c) <= RADIUS:
                    out.append(x)
            return out
        for x in obj:
            out += nearby(x)
    elif isinstance(obj, dict):
        for v in obj.values():
            out += nearby(v)
    return out


def text(x):
    if isinstance(x, dict):
        return x.get("th") or x.get("en") or ""
    return x or ""


def main():
    latest_path = os.path.join(ROOT, "latest.json")
    try:
        prev = json.load(open(latest_path, encoding="utf-8"))
    except (OSError, ValueError):
        prev = {"data": {}, "sources": {}}

    data, meta = {}, {}
    for key, path in SOURCES.items():
        try:
            rows = nearby(get(path))
            data[key] = rows
            meta[key] = {"ok": True, "fetched_at": iso(now), "count": len(rows)}
            print(f"[ok] {key}: {len(rows)} records")
        except Exception as e:  # noqa: BLE001
            # ต้นทางล่ม → ใช้ข้อมูลรอบก่อน พร้อมเวลาเดิม
            data[key] = prev.get("data", {}).get(key, [])
            old = prev.get("sources", {}).get(key, {})
            meta[key] = {"ok": False, "error": str(e)[:200], "fetched_at": old.get("fetched_at"), "count": len(data[key])}
            print(f"[fail] {key}: {e}")

    if not any(m["ok"] for m in meta.values()):
        raise SystemExit("ดึงไม่ได้สักแหล่ง — ไม่เขียนไฟล์ทับ")

    os.makedirs(ROOT, exist_ok=True)
    json.dump({"generated_at": iso(now), "center": [LAT, LNG], "radius_km": RADIUS, "sources": meta, "data": data},
              open(latest_path, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))

    # ---------- history: ระดับน้ำย้อนหลังต่อสถานี ----------
    hist_path = os.path.join(ROOT, "history.json")
    try:
        hist = json.load(open(hist_path, encoding="utf-8"))
    except (OSError, ValueError):
        hist = {"stations": {}}

    for r in data["waterlevel"] + data["canal"]:
        st = r.get("station") or r.get("canal_station") or r
        sid = str(st.get("id") or st.get("tele_station_oldcode") or text(st.get("tele_station_name")))
        t = r.get("waterlevel_datetime") or r.get("canal_waterlevel_datetime")
        msl = num(r.get("waterlevel_msl", r.get("canal_waterlevel_value")))
        if not sid or not t or msl is None:
            continue
        h = hist["stations"].setdefault(sid, {"name": text(st.get("tele_station_name") or st.get("canal_station_name")), "points": []})
        if not h["points"] or h["points"][-1][0] != t:
            h["points"].append([t, msl, num(r.get("storage_percent"))])

    # เวลาในข้อมูลเป็นเวลาไทย (UTC+7)
    cutoff = (now + timedelta(hours=7) - timedelta(days=HISTORY_DAYS)).strftime("%Y-%m-%d %H:%M")
    for sid in list(hist["stations"]):
        pts = [p for p in hist["stations"][sid]["points"] if str(p[0]).replace("T", " ")[:16] >= cutoff]
        if pts:
            hist["stations"][sid]["points"] = pts
        else:
            del hist["stations"][sid]
    hist["updated_at"] = iso(now)
    json.dump(hist, open(hist_path, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print("done", iso(now))


if __name__ == "__main__":
    main()
