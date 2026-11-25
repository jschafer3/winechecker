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
