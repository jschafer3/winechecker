#!/usr/bin/env python3
"""WineChecker: combine lots + prices into site/view.json.

Run:  python3 pipeline/value.py 187

Inputs (only lots.json is required):
  data/<id>/lots.json        from scraper/parse_lots.py
  data/<id>/prices.json      list of {lot_id, source, price_750_hkd, url, date, confidence}
  data/<id>/overrides.csv    lot_id,price_750_hkd,note   (your own prices; always win)
  data/<id>/results_past.json  optional past Madison hammer prices (same wine key)

Value math (see plan):
  H      = current bid, else low estimate
  Cost   = H x (1 + 22.5%)
  Value  = M x eq750           M = market price per 750 ml, HKD
  Gap    = Value - Cost        (+ = you save)
  Gap %  = (Cost - Value) / Value   (- = under market)
  Walk-away bid = Value / 1.225, rounded down to a valid Madison bid step
"""
import csv
import json
import os
import sys
from datetime import date

PREMIUM = 0.225
BAND_PCT = 10.0  # +/- band for "at market"

# Madison bid increment table (auction 187 data, priceLevel): from this amount, the step is ...
BID_STEPS = sorted({
    0: 100, 2000: 200, 3200: 300, 3800: 200, 4200: 300, 4800: 200, 5000: 500,
    10000: 1000, 20000: 2000, 32000: 3000, 38000: 2000, 42000: 3000, 48000: 2000,
    50000: 5000, 100000: 10000, 200000: 20000, 320000: 30000, 380000: 20000,
    420000: 30000, 480000: 20000, 500000: 50000, 2000000: 100000,
}.items())

CONF_RANK = {"manual": 4, "exact": 3, "likely": 2, "check": 1}


def round_down_to_bid(amount):
    """Largest valid bid that is <= amount."""
    if amount is None or amount <= 0:
        return None
    base, step = BID_STEPS[0]
    for b, s in BID_STEPS:
        if amount >= b:
            base, step = b, s
    return int(base + ((amount - base) // step) * step)


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_overrides(path):
    out = {}
    if not os.path.exists(path):
        return out
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try:
                out[int(r["lot_id"])] = {"price_750_hkd": float(r["price_750_hkd"]),
                                         "note": r.get("note", "")}
            except (KeyError, ValueError):
                print("skip bad override row:", r)
    return out


def pick_price(lot, prices_by_lot, overrides):
    """Return (price_750_hkd, source, confidence, url) by priority."""
    lid = lot["lot_id"]
    if lid in overrides:
        return overrides[lid]["price_750_hkd"], "manual", "manual", ""
    cands = [p for p in prices_by_lot.get(lid, []) if p.get("price_750_hkd")]
    if cands:
        best = max(cands, key=lambda p: (CONF_RANK.get(p.get("confidence"), 0), p.get("date", "")))
        return best["price_750_hkd"], best.get("source", "?"), best.get("confidence", "check"), best.get("url", "")
    # Fallback: Madison estimate midpoint per 750 ml incl. premium (house view, not market)
    if lot.get("est_low") and lot.get("est_high") and lot.get("eq750"):
        mid = (lot["est_low"] + lot["est_high"]) / 2 * (1 + PREMIUM) / lot["eq750"]
        return round(mid, 2), "house", "house", ""
    return None, "none", "none", ""


def value_row(lot, m750, source, conf, url):
    hammer = lot.get("current") or lot.get("est_low")
    eq = lot.get("eq750")
    row = {k: lot[k] for k in ("lot_id", "lot_no", "url", "title", "category", "colour", "vintage",
                               "producer", "wine", "region", "qty_text", "parts", "bottles",
                               "bottle_ml", "eq750", "packing", "score", "est_low", "est_high",
                               "current", "status", "mixed", "needs_check")}
    row.update({"hammer": hammer, "price_750": m750, "price_source": source,
                "price_conf": conf, "price_url": url})
    if hammer is None:
        return row
    cost = hammer * (1 + PREMIUM)
    row["cost"] = round(cost, 2)
    row["cost_per_750"] = round(cost / eq, 2) if eq else None
    if m750 and eq and source != "house":
        value = m750 * eq
        gap = value - cost
        gap_pct = (cost - value) / value * 100
        row.update({
            "value": round(value, 2),
            "gap": round(gap, 2),
            "gap_pct": round(gap_pct, 1),
            "band": "under" if gap_pct < -BAND_PCT else ("over" if gap_pct > BAND_PCT else "at"),
            "walk_away": round_down_to_bid(value / (1 + PREMIUM)),
        })
    elif source == "house":
        row["band"] = "house"
    else:
        row["band"] = "none"
    return row


def main(aid):
    d = os.path.join("data", aid)
    lots = load_json(os.path.join(d, "lots.json"), None)
    if lots is None:
        sys.exit(f"missing {d}/lots.json")
    prices = load_json(os.path.join(d, "prices.json"), [])
    if isinstance(prices, dict):
        prices = prices.get("prices", [])
    by_lot = {}
    for p in prices:
        by_lot.setdefault(int(p["lot_id"]), []).append(p)
    overrides = load_overrides(os.path.join(d, "overrides.csv"))

    rows = []
    for lot in lots["lots"]:
        m, src, conf, url = pick_price(lot, by_lot, overrides)
        rows.append(value_row(lot, m, src, conf, url))

    out = {"auction_id": lots["auction_id"], "premium_pct": PREMIUM * 100, "band_pct": BAND_PCT,
           "built": date.today().isoformat(), "lots": rows}
    os.makedirs("site", exist_ok=True)
    with open("site/view.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    wine = [r for r in rows if r["category"] == "Wine"]
    count = lambda k: sum(1 for r in wine if r.get("band") == k)
    print(f"{len(rows)} lots -> site/view.json")
    print(f"wine: under {count('under')}, at {count('at')}, over {count('over')}, "
          f"house estimate only {count('house')}, no price {count('none')}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "187")
