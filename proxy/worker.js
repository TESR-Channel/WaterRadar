// Cloudflare Worker: CORS proxy สำหรับ ThaiWater API (สำรอง ใช้เมื่อ GitHub Actions ดึงไม่ได้)
// Deploy: dash.cloudflare.com > Workers & Pages > Create > Worker > วางโค้ดนี้ > Deploy
// แล้วเอา URL (เช่น https://tesr-water.<account>.workers.dev) ไปใส่ช่อง Proxy URL ในหน้าเว็บ
const UPSTREAM = 'https://api-v3.thaiwater.net/api/v1/thaiwater30';
const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, OPTIONS',
  'Access-Control-Allow-Headers': 'Accept, Content-Type',
};

export default {
  async fetch(req) {
    if (req.method === 'OPTIONS') return new Response(null, { headers: CORS });
    const url = new URL(req.url);
    // อนุญาตเฉพาะ endpoint ที่หน้าเว็บใช้ กันคนเอา proxy ไปใช้อย่างอื่น
    if (!/^\/(public|analyst)\/[\w\/]+$/.test(url.pathname)) {
      return new Response('Not allowed', { status: 403, headers: CORS });
    }
    const upstream = await fetch(UPSTREAM + url.pathname + url.search, {
      headers: {
        'Accept': 'application/json',
        'User-Agent': 'Mozilla/5.0 (TESR Water Watch)',
        'Referer': 'https://www.thaiwater.net/',
      },
      cf: { cacheTtl: 120, cacheEverything: true }, // cache 2 นาที ลดโหลดต้นทาง
    });
    return new Response(upstream.body, {
      status: upstream.status,
      headers: { ...CORS, 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'public, max-age=120' },
    });
  },
};
