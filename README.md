# WaterRadar — ระดับน้ำรอบหมู่บ้านมณียา

หน้าเว็บติดตามระดับน้ำเจ้าพระยา คลอง ฝน 24 ชม. ถนนน้ำท่วม เรดาร์ฝน และ CCTV รอบ ต.ไทรม้า นนทบุรี
ข้อมูลจากคลังข้อมูลน้ำแห่งชาติ สสน. (thaiwater.net) · by TESR

## ทำงานยังไง
```
GitHub Actions (ทุก 10 นาที) ──► scripts/fetch_water.py ──► data/latest.json + data/history.json ──► commit
                                                                                              │
GitHub Pages (index.html) ◄───────────────── อ่านไฟล์ JSON ใน repo เดียวกัน (ไม่ติด CORS) ◄──────┘
```
ถ้า `data/latest.json` เก่ากว่า 3 ชม. หน้าเว็บจะลองดึงสดจาก API เอง (หรือผ่าน proxy ใน `proxy/worker.js`)

## ตั้งค่าครั้งแรก
1. **Settings → Pages** → Source: *Deploy from a branch* → `main` / `(root)` → Save
2. **Settings → Actions → General** → Workflow permissions: *Read and write permissions* → Save
3. **Actions → Fetch water data → Run workflow** (รันครั้งแรกด้วยมือ ดู log ว่าขึ้น `[ok]` ครบไหม)
4. เปิด `https://tesr-channel.github.io/WaterRadar/`

## ปรับแต่ง
- พิกัดหมู่บ้าน / รัศมี: แก้ `HOME_LAT`, `HOME_LNG`, `RADIUS_KM` ใน `.github/workflows/fetch-water.yml` และปรับในหน้า "ตั้งค่า" ของเว็บให้ตรงกัน
- เกณฑ์เฝ้าระวัง (% ตลิ่ง) และความถี่รีเฟรชหน้าเว็บ: หน้า "ตั้งค่า"

## เกณฑ์สถานะ
| สถานะ | เงื่อนไข |
|---|---|
| ปลอดภัย | ต่ำกว่า 80% ของตลิ่ง |
| เฝ้าระวัง | 80–100% |
| วิกฤต | เกิน 100% หรือถึงระดับวิกฤตของสถานี |

> ใช้ประกอบการตัดสินใจเท่านั้น ติดตามประกาศทางการจาก ปภ. (1784) และเทศบาลควบคู่กัน
