// WineChecker: lot scraper for one Madison Auction sale.
//
// What it does:
//   1. Opens https://www.madison-auction.com/auction/<id>?pn=<page> in a headless browser.
//   2. Reads each lot card that the page shows to a normal visitor.
//   3. Writes data/<id>/lots_raw.tsv (one line per lot).
//
// Rules:
//   - Read-only. No login. No bids. No calls to the site's private API.
//   - One browser. Wait 1.5 s between pages.
//
// Run:  npm install playwright   (once)
//       node scraper/scrape_lots.js 187
//
// Then: python3 scraper/parse_lots.py data/187/lots_raw.tsv data/187/lots.json

const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const AUCTION = process.argv[2] || '187';
const BASE = 'https://www.madison-auction.com';
const WAIT_MS = 1500;
const OUT_DIR = path.join(__dirname, '..', 'data', AUCTION);

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// Turn one lot card's visible text into one TSV row.
// Fields: lot_id | lot_no | title | qty | score | est_low | est_high | current | status
function cardToRow(href, text) {
  const lines = text.split('\n').map((s) => s.trim()).filter((s) => s && s !== 'View Lot Details');
  const lotNo = (lines[0] || '').replace(/^Lot\s+/, '');
  const title = lines[1] || '';
  const qty = lines[2] || '';
  const score = lines[3] && /^(RP|WA|JS|WS|VM|JR|BH|AG|NM|D)\b/.test(lines[3]) ? lines[3] : '';
  const hkd = text.match(/HKD\s?[\d,]+/g) || [];
  const cur = (text.match(/Current Price\s*\n?\s*HKD\s?([\d,]+)/) || [])[1] || '';
  const status = lines.find((s) => /^(ACCEPTING BIDS|SOLD|PASSED|CLOSED|UNSOLD|LIVE)/i.test(s)) || '';
  const num = (s) => (s || '').replace(/\D/g, '');
  return [href.split('/').pop(), lotNo, title, qty, score, num(hkd[0]), num(hkd[1]), num(cur), status]
    .map((v) => String(v).replace(/[|\n]/g, ' '))
    .join('|');
}

async function readCards(page) {
  await page.waitForSelector(`a[href*="/auction/${AUCTION}/lot/"]`, { timeout: 30000 });
  await sleep(800); // let prices render
  return page.$$eval(`a[href*="/auction/${AUCTION}/lot/"]`, (as) =>
    as.map((a) => ({ href: a.getAttribute('href'), text: a.innerText }))
  );
}

async function pageCount(page) {
  const nums = await page.$$eval('button.MuiPaginationItem-root', (bs) =>
    bs.map((b) => parseInt(b.textContent.trim(), 10)).filter((n) => n > 0)
  );
  return nums.length ? Math.max(...nums) : 1;
}

(async () => {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({ userAgent: 'WineChecker/0.1 (private, read-only, 1 req per 1.5s)' });

  await page.goto(`${BASE}/auction/${AUCTION}`, { waitUntil: 'domcontentloaded' });
  const seen = new Map();
  for (const c of await readCards(page)) seen.set(c.href, c.text);
  const pages = await pageCount(page);
  console.log(`Auction ${AUCTION}: ${pages} pages`);

  for (let p = 2; p <= pages; p++) {
    await sleep(WAIT_MS);
    await page.goto(`${BASE}/auction/${AUCTION}?pn=${p}`, { waitUntil: 'domcontentloaded' });
    const cards = await readCards(page);
    for (const c of cards) seen.set(c.href, c.text);
    console.log(`page ${p}: ${cards.length} cards, total ${seen.size}`);
  }
  await browser.close();

  const header = 'lot_id|lot_no|title|qty|score|est_low|est_high|current|status';
  const rows = [...seen].map(([h, t]) => cardToRow(h, t));
  const out = path.join(OUT_DIR, 'lots_raw.tsv');
  fs.writeFileSync(out, [header, ...rows].join('\n') + '\n');
  console.log(`Wrote ${rows.length} lots to ${out}`);
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
