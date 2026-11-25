#!/usr/bin/env python3
"""WineChecker: turn lots_raw.tsv into lots.json.

Run:  python3 scraper/parse_lots.py data/187/lots_raw.tsv data/187/lots.json

For each lot it finds:
  vintage, producer, wine (cuvee/appellation), colour, region, category,
  bottles, size per bottle, total ml, 750 ml equivalents, packing, mixed flag.

Rules are simple keyword rules. A lot that does not fit gets "needs_check": true.
"""
import json
import re
import sys

# --- Keyword tables ---------------------------------------------------------

PRODUCERS = [
    # (match text, producer name, region)
    ("Lafite Rothschild", "Château Lafite Rothschild", "Bordeaux"),
    ("Lafite", "Château Lafite Rothschild", "Bordeaux"),
    ("Mouton Rothschild", "Château Mouton Rothschild", "Bordeaux"),
    ("La Mission Haut-Brion", "Château La Mission Haut-Brion", "Bordeaux"),
    ("Haut-Brion", "Château Haut-Brion", "Bordeaux"),
    ("Haut Brion", "Château Haut-Brion", "Bordeaux"),
    ("Château Margaux", "Château Margaux", "Bordeaux"),
    ("Château Latour", "Château Latour", "Bordeaux"),
    ("Lynch-Bages", "Château Lynch-Bages", "Bordeaux"),
    ("Talbot", "Château Talbot", "Bordeaux"),
    ("Cos d'Estournel", "Cos d'Estournel", "Bordeaux"),
    ("Montrose", "Château Montrose", "Bordeaux"),
    ("Pichon Longueville Comtesse", "Château Pichon Longueville Comtesse de Lalande", "Bordeaux"),
    ("Angélus", "Château Angélus", "Bordeaux"),
    ("Ausone", "Château Ausone", "Bordeaux"),
    ("Cheval Blanc", "Château Cheval Blanc", "Bordeaux"),
    ("Figeac", "Château Figeac", "Bordeaux"),
    ("Pavie Decesse", "Château Pavie Decesse", "Bordeaux"),
    ("Pavie", "Château Pavie", "Bordeaux"),
    ("Bellevue-Mondotte", "Château Bellevue-Mondotte", "Bordeaux"),
    ("La Mondotte", "La Mondotte", "Bordeaux"),
    ("La Fleur-Pétrus", "Château La Fleur-Pétrus", "Bordeaux"),
    ("Pétrus", "Pétrus", "Bordeaux"),
    ("Lafleur", "Château Lafleur", "Bordeaux"),
    ("Hosanna", "Château Hosanna", "Bordeaux"),
    ("La Violette", "Château La Violette", "Bordeaux"),
    ("Latour-a-Pomerol", "Château Latour à Pomerol", "Bordeaux"),
    ("Trotanoy", "Château Trotanoy", "Bordeaux"),
    ("Vieux Château Certan", "Vieux Château Certan", "Bordeaux"),
    ("Pavillon Rouge", "Château Margaux", "Bordeaux"),
    ("Billecart-Salmon", "Billecart-Salmon", "Champagne"),
    ("Dom Pérignon", "Dom Pérignon", "Champagne"),
    ("Jacquesson", "Jacquesson", "Champagne"),
    ("Roederer", "Louis Roederer", "Champagne"),
    ("Cristal", "Louis Roederer", "Champagne"),
    ("Pol Roger", "Pol Roger", "Champagne"),
    ("Taittinger", "Taittinger", "Champagne"),
    ("Salon", "Salon", "Champagne"),
    ("Charles Heidsieck", "Charles Heidsieck", "Champagne"),
    ("Dauvissat", "Domaine René et Vincent Dauvissat", "Burgundy"),
    ("Carillon", "Louis Carillon", "Burgundy"),
    ("d'Auvenay", "Domaine d'Auvenay", "Burgundy"),
    ("Chartron", "Jean-Michel Chartron", "Burgundy"),
    ("Leflaive", "Domaine Leflaive", "Burgundy"),
    ("Niellon", "Domaine Michel Niellon", "Burgundy"),
    ("Ramonet", "Domaine Ramonet", "Burgundy"),
    ("Joseph Drouhin", "Joseph Drouhin", "Burgundy"),
    ("Drouhin-Laroze", "Domaine Drouhin-Laroze", "Burgundy"),
    ("Gagnard-Delagrange", "Gagnard-Delagrange", "Burgundy"),
    ("Louis Jadot", "Louis Jadot", "Burgundy"),
    ("Louis Latour", "Louis Latour", "Burgundy"),
    ("Armand Rousseau", "Domaine Armand Rousseau", "Burgundy"),
    ("Faiveley", "Faiveley", "Burgundy"),
    ("Fourrier", "Domaine Jean-Marie Fourrier", "Burgundy"),
    ("Romanée-Conti", "Domaine de la Romanée-Conti", "Burgundy"),
    ("René Engel", "Domaine René Engel", "Burgundy"),
    ("Arnaud Ente", "Domaine Arnaud Ente", "Burgundy"),
    ("Coche-Dury", "Coche-Dury", "Burgundy"),
    ("Comtes Lafon", "Domaine des Comtes Lafon", "Burgundy"),
    ("Leroy", "Domaine Leroy", "Burgundy"),
    ("Lambrays", "Clos des Lambrays", "Burgundy"),
    ("Mugneret-Gibourg", "Georges Mugneret-Gibourg", "Burgundy"),
    ("Mongeard-Mugneret", "Domaine Mongeard-Mugneret", "Burgundy"),
    ("Gerard Mugneret", "Gérard Mugneret", "Burgundy"),
    ("Duroché", "Domaine Duroché", "Burgundy"),
    ("Roumier", "Domaine Georges Roumier", "Burgundy"),
    ("Bachelet", "Bachelet", "Burgundy"),
    ("Bernard Moreau", "Bernard Moreau", "Burgundy"),
    ("Hospices de Beaune", "Hospices de Beaune", "Burgundy"),
    ("Roulot", "Domaine Roulot", "Burgundy"),
    ("Lachaux", "Charles Lachaux", "Burgundy"),
    ("William Kelley", "William Kelley", "Burgundy"),
    ("Lucien Le Moine", "Lucien Le Moine", "Burgundy"),
    ("Denis Mortet", "Domaine Denis Mortet", "Burgundy"),
    ("Truchot", "Jacky Truchot", "Burgundy"),
    ("Jean-Marc Millot", "Jean-Marc Millot", "Burgundy"),
    ("Lamarche", "Domaine François Lamarche", "Burgundy"),
    ("Liger-Belair", "Domaine du Comte Liger-Belair", "Burgundy"),
    ("Emmanuel Rouget", "Domaine Emmanuel Rouget", "Burgundy"),
    ("Henri Jayer", "Henri Jayer", "Burgundy"),
    ("Rayas", "Château Rayas", "Rhône"),
    ("Prieuré Saint Christophe", "Domaine Prieuré Saint Christophe", "Savoie"),
    ("Bruno Giacosa", "Bruno Giacosa", "Piedmont"),
    ("Caymus", "Caymus Vineyards", "California"),
    ("Harlan", "Harlan Estate", "California"),
    ("Schrader", "Schrader Cellars", "California"),
    ("Penfolds", "Penfolds", "South Australia"),
]

WHITE_WORDS = ["Montrachet", "Meursault", "Chablis", "Puligny", "Aligoté", "Les Clous",
               "Blanc", "White", "Corton-Charlemagne"]
CHAMPAGNE_REGION = "Champagne"

SIZE_RE = re.compile(r"(\d+)\s*x\s*([\d.]+)\s*(ml|l)\b", re.I)
SINGLE_SIZE_RE = re.compile(r"^([\d.]+)\s*(ml|l)\b", re.I)
VINTAGE_RE = re.compile(r"^(1[89]\d\d|20[0-2]\d)\b")


def parse_qty(qty):
    """'12 x 750ml (2 Sealed OWC)' -> parts, packing."""
    packing = ""
    m = re.search(r"\(([^)]*)\)", qty)
    if m:
        packing = m.group(1)
    parts = []
    for n, size, unit in SIZE_RE.findall(qty):
        ml = float(size) * (1000 if unit.lower() == "l" else 1)
        parts.append({"count": int(n), "ml": int(round(ml))})
    if not parts:
        m = SINGLE_SIZE_RE.match(qty.strip())
        if m:  # e.g. '750ml (OWC)' with no count: count unknown
            ml = float(m.group(1)) * (1000 if m.group(2).lower() == "l" else 1)
            parts.append({"count": None, "ml": int(round(ml))})
    return parts, packing


def find_producer(title):
    for key, name, region in PRODUCERS:
        if key.lower() in title.lower():
            return name, region
    return "", ""


def colour_of(title, region):
    if region == CHAMPAGNE_REGION or "champagne" in title.lower():
        return "Champagne"
    if "Pavillon Rouge & Blanc" in title:
        return "Mixed"
    if any(w.lower() in title.lower() for w in WHITE_WORDS):
        return "White"
    return "Red"


def parse_row(row):
    lot_id, lot_no, title, qty, score, lo, hi, cur, status = row
    lot_no_i = int(lot_no)
    parts, packing = parse_qty(qty)
    bottles = sum(p["count"] for p in parts) if parts and all(p["count"] for p in parts) else None
    total_ml = sum(p["count"] * p["ml"] for p in parts) if bottles else None
    single_size = parts[0]["ml"] if len(parts) == 1 else None

    category = "Spirits" if lot_no_i >= 8000 else "Wine"
    vm = VINTAGE_RE.match(title)
    vintage = int(vm.group(1)) if vm else None
    # A wine lot is "single" when it has one vintage and one bottle size.
    mixed = category == "Wine" and (vintage is None or len(parts) != 1 or "&" in title.split(" ")[0])

    producer, region = find_producer(title) if category == "Wine" else ("", "")
    wine_name = VINTAGE_RE.sub("", title).strip() if vintage else title
    colour = colour_of(title, region) if category == "Wine" else ""

    needs_check = category == "Wine" and (not producer or bottles is None)

    return {
        "lot_id": int(lot_id),
        "lot_no": lot_no_i,
        "url": f"https://www.madison-auction.com/auction/187/lot/{lot_id}",
        "title": title,
        "category": category,
        "colour": colour,
        "vintage": vintage,
        "producer": producer,
        "wine": wine_name,
        "region": region,
        "qty_text": qty,
        "parts": parts,
        "bottles": bottles,
        "bottle_ml": single_size,
        "total_ml": total_ml,
        "eq750": round(total_ml / 750, 2) if total_ml else None,
        "packing": packing,
        "score": score,
        "est_low": int(lo) if lo else None,
        "est_high": int(hi) if hi else None,
        "current": int(cur) if cur else None,
        "status": status,
        "mixed": mixed,
        "needs_check": needs_check,
    }


def main(src, dst):
    with open(src, encoding="utf-8") as f:
        lines = [l.rstrip("\n") for l in f if l.strip()]
    rows = [l.split("|") for l in lines[1:]]
    bad = [r for r in rows if len(r) != 9]
    if bad:
        sys.exit(f"{len(bad)} rows do not have 9 fields, first: {bad[0]}")
    lots = sorted((parse_row(r) for r in rows), key=lambda x: x["lot_no"])
    with open(dst, "w", encoding="utf-8") as f:
        json.dump({"auction_id": 187, "premium_pct": 22.5, "currency": "HKD", "lots": lots},
                  f, ensure_ascii=False, indent=1)
    wine = [l for l in lots if l["category"] == "Wine"]
    print(f"{len(lots)} lots, {len(wine)} wine, {len(lots) - len(wine)} spirits")
    print("colour:", {c: sum(1 for l in wine if l["colour"] == c) for c in {l['colour'] for l in wine}})
    print("single-wine lots:", sum(1 for l in wine if not l["mixed"]))
    print("needs check:", sum(1 for l in wine if l["needs_check"]))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
