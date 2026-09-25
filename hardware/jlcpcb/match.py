#!/usr/bin/env python3
"""Match luftctl BOM lines to in-stock JLCPCB/LCSC parts using the jlcparts DB.

Reads bom_raw.csv (exported by kicad-cli) and the jlcparts cache.sqlite3.
For passives it matches parametrically (value + package); for ICs/connectors/
switches it matches by manufacturer part number (mfr) substring.
Prints a per-line report and writes candidates.json for the assignment step.
"""
import csv, json, re, sqlite3, sys, unicodedata
from pathlib import Path

DB = "/tmp/jlcparts/cache.sqlite3"
BOM = Path(__file__).with_name("bom_raw.csv")

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row

# ---- value parsing -------------------------------------------------------
OHM = "Ω"
def norm(s):
    return unicodedata.normalize("NFKC", s or "").strip()

def to_ohms(s):
    s = norm(s).replace(OHM, "").replace("ohm", "").replace("Ohm", "")
    m = re.fullmatch(r"([0-9.]+)\s*([mkKMG]?)", s)
    if not m: return None
    v = float(m.group(1)); p = m.group(2)
    return v * {"":1,"m":1e-3,"k":1e3,"K":1e3,"M":1e6,"G":1e9}[p]

def to_farads(s):
    s = norm(s).replace("F","").replace("µ","u").replace("μ","u")
    m = re.fullmatch(r"([0-9.]+)\s*([pnum]?)", s)
    if not m: return None
    v = float(m.group(1)); p = m.group(2)
    return v * {"":1,"p":1e-12,"n":1e-9,"u":1e-6,"µ":1e-6,"m":1e-3}[p]

def price_1k(pstr):
    """Approx unit price near qty 100-1000 from 'a-b:price,...' string."""
    best = None
    for seg in (pstr or "").split(","):
        if ":" not in seg: continue
        try: p = float(seg.split(":")[1])
        except ValueError: continue
        best = p if best is None else min(best, p)
    return best

def rows(where, params=()):
    q = ("SELECT lcsc,category,subcategory,mfr,manufacturer,package,library_type,"
         "preferred,stock,description,attributes,price,assembly_mode "
         "FROM jlc_components WHERE stock>0 AND " + where)
    return [dict(r) for r in con.execute(q, params)]

def attr(r, key):
    try: return json.loads(r["attributes"]).get(key)
    except Exception: return None

def fmt(r, extra=""):
    lt = "BASE" if r["library_type"] == "base" else ("PREF" if r["preferred"] else "ext")
    return (f"  C{r['lcsc']:<8} stock={r['stock']:>7}  ${price_1k(r['price']):<8} "
            f"{lt:4} {r['assembly_mode']:10} {r['package']:22} {r['mfr']:24} {extra}")

# ---- per-part matchers ---------------------------------------------------
def match_resistor(target_ohms):
    c = rows("category='Resistors' AND package='0805'")
    out = []
    for r in c:
        o = to_ohms(attr(r, "Resistance") or "")
        if o is None: continue
        if abs(o - target_ohms) <= max(1.0, target_ohms*0.005):
            r["_tol"] = attr(r, "Tolerance"); out.append(r)
    return rank(out)

def match_capacitor(target_f, want_np0=False):
    c = rows("category='Capacitors' AND package='0805'")
    out = []
    for r in c:
        f = to_farads(attr(r, "Capacitance") or "")
        if f is None: continue
        if abs(f - target_f) <= target_f*0.02:
            r["_tc"] = attr(r, "Temperature Coefficient")
            r["_v"]  = attr(r, "Voltage Rating")
            out.append(r)
    if want_np0:
        np0 = [r for r in out if (r["_tc"] or "").upper() in ("C0G","NP0","C0G/NP0")]
        out = np0 or out
    return rank(out, cap=True)

def match_like(where, params):
    return rank(rows(where, params))

def volt(r):
    v = to_ohms((r.get("_v") or "0").replace("V","")+OHM) or 0
    return v

def rank(lst, cap=False):
    def key(r):
        return (0 if r["library_type"]=="base" else 1,
                0 if r["preferred"] else 1,
                -(volt(r) if cap else 0),      # prefer higher voltage caps
                -(r["stock"]),
                (price_1k(r["price"]) or 9e9))
    return sorted(lst, key=key)

# ---- run over the BOM ----------------------------------------------------
report = []
assign = {}   # designator-group value -> chosen lcsc + note

def show(name, cands, note=""):
    print(f"\n### {name}   {note}")
    if not cands:
        print("  !! NO in-stock match")
    for r in cands[:5]:
        extra = f"{attr(r,'Resistance') or attr(r,'Capacitance') or ''} " \
                f"{r.get('_tol') or r.get('_tc') or ''} {r.get('_v') or ''}"
        print(fmt(r, extra))
    return cands[0]["lcsc"] if cands else None

with open(BOM, newline="") as f:
    bom = list(csv.DictReader(f))

for line in bom:
    des, val, fp = line["Designator"], line["Comment"], line["Footprint"]
    pref = des.split(",")[0].rstrip("0123456789")
    key = f"{val} | {fp}"
    chosen = None
    if pref == "R":
        chosen = show(f"{des}  R {val}", match_resistor(to_ohms(val)))
    elif pref == "C":
        chosen = show(f"{des}  C {val}", match_capacitor(to_farads(val), want_np0=(to_farads(val)<=1e-9)))
    elif pref == "FB":
        chosen = show(f"{des}  Ferrite {val}",
            match_like("category IN ('Inductors, Coils, Chokes','Filters') AND package='0805' "
                       "AND (subcategory LIKE '%errite%' OR subcategory LIKE '%Bead%')", ()))
    elif des == "L1":
        chosen = show("L1  inductor 10uH SRN6045",
            match_like("mfr LIKE 'SRN6045%' AND (mfr LIKE '%100%' OR mfr LIKE '%10U%')", ()))
    elif des == "D1":
        chosen = show("D1  1N5819 SOD-123",
            match_like("(mfr LIKE '%1N5819%' OR description LIKE '%1N5819%') AND package LIKE 'SOD-123%'", ()))
    elif pref == "D":  # LEDs
        chosen = show(f"{des}  LED 0805 ({val})",
            match_like("category='Optoelectronics' AND subcategory LIKE '%Light Emitting Diodes%' AND package='0805'", ()))
    elif des == "U1":
        chosen = show("U1  LMR62014XMF SOT-23-5",
            match_like("mfr LIKE 'LMR62014%'", ()))
    elif des == "U2":
        chosen = show("U2  MIC5504-3.3YM5 SOT-23-5",
            match_like("mfr LIKE 'MIC5504-3.3%'", ()))
    elif des == "U3":
        chosen = show("U3  USBLC6-4SC6 SOT-23-6",
            match_like("mfr LIKE 'USBLC6-4SC6%'", ()))
    elif des == "U4":
        chosen = show("U4  ESP32-C3-WROOM-02",
            match_like("mfr LIKE 'ESP32-C3-WROOM-02%'", ()))
    elif des == "J1":
        chosen = show("J1  USB-C HRO TYPE-C-31-M-12",
            match_like("mfr LIKE '%TYPE-C-31-M-12%'", ()))
    elif pref == "J" and val in ("UART","I2C"):
        chosen = show(f"{des}  JST SH SM04B-SRSS-TB",
            match_like("mfr LIKE 'SM04B-SRSS-TB%'", ()))
    elif pref == "J":  # fan pin header 1x4 2.54 THT
        chosen = show(f"{des}  pin header 1x4 2.54mm",
            match_like("subcategory LIKE '%Pin Header%' AND (description LIKE '%2.54%') "
                       "AND (description LIKE '%1x4%' OR description LIKE '%1X4%' OR description LIKE '%4P%' OR mfr LIKE '%04%')", ()))
    elif des in ("JP1","SW1"):
        chosen = show(f"{des}  switch PTS810",
            match_like("mfr LIKE 'PTS810%'", ()))
    else:
        print(f"\n### {des}  {val}  ({fp}) -- skipped (non-assembly)")
    assign[des] = chosen

print("\n\n===== SUMMARY =====")
for line in bom:
    des = line["Designator"]
    c = assign.get(des)
    tag = f"C{c}" if c else "-- UNMATCHED --"
    print(f"  {des:16} {line['Comment']:26} {tag}")

Path(__file__).with_name("assign.json").write_text(json.dumps(assign, indent=2))
