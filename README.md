# WineChecker

Private tool for 3 friends. It lists all lots of a Madison Auction sale, filters them, and compares each lot to a market price (HKD and %).

Plan: https://claude.ai/artifact/AYBw9ZDGWRDGrvWT8VQ3LB

## Phase 1: lot data

| Step | Command | Output |
|---|---|---|
| 1. Scrape (read-only, public pages) | `npm install playwright && node scraper/scrape_lots.js 187` | `data/187/lots_raw.tsv` |
| 2. Parse | `python3 scraper/parse_lots.py data/187/lots_raw.tsv data/187/lots.json` | `data/187/lots.json` |

Rules: no login from code, no bids, no calls to the site's private API, 1.5 s between pages.

Auction 187 (2026 December Auction, live 12 Dec 2026 11:00 HKT): 369 lots, 285 wine, 84 spirits. Buyer's premium 22.5%.

`needs_check: true` marks mixed lots with no single producer. They need the lot page detail before we can price them.

## Phase 2: browse page

`site/index.html` reads `site/lots.json` (a copy of `data/187/lots.json`).

Open it on your computer:

```
cp data/187/lots.json site/lots.json
cd site && python3 -m http.server 8000
```

Then go to http://localhost:8000. Filters: type, region, producer, vintage range, max HKD per bottle, bottle size, single or mixed lots. Sort by lot, price per bottle, lot price, vintage, or score. Prices include the 22.5% premium by default. Stars are saved in your browser only (shared stars come in phase 5).

## Phase 3: market value

```
python3 pipeline/value.py 187     # writes site/view.json
```

Price order per lot: `data/187/overrides.csv` (your own price) > `data/187/prices.json` (Vivino, wineapi.io, past Madison sales; best confidence wins) > Madison estimate only ("No market price yet").

To set your own price, add a line to `overrides.csv`: `lot_id,price_750_hkd,note` (price per 750 ml in HKD).

Badges: Under / At market / Over by more than 10% after the 22.5% premium. Walk-away bid = market value ÷ 1.225, rounded down to a valid Madison bid step.
