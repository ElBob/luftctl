#!/usr/bin/env python3
"""Build the JLCPCB assembly BOM from bom_raw.csv + verified LCSC assignments,
and emit a verification report. LCSC numbers were verified in-stock against
the jlcparts cache.sqlite3 snapshot fetched 2026-09-24."""
import csv, json, sqlite3
from pathlib import Path

HERE = Path(__file__).parent
DB = sqlite3.connect("/tmp/jlcparts/cache.sqlite3"); DB.row_factory = sqlite3.Row

# first-designator -> (lcsc or None, note). None = no in-stock match in this DB.
ASSIGN = {
    "C1":  (7472969,  "4.7uF X5R 50V"),
    "C3":  (6641028,  "1uF X7R 100V"),
    "C5":  (7503487,  "100nF X7R 100V"),
    "C6":  (7393918,  "220pF C0G 500V — LOW STOCK (only in-stock option)"),
    "C8":  (16194907, "10uF X7S 25V"),
    "D1":  (6562211,  "1N5819W Schottky SOD-123"),
    "D2":  (7496834,  "Red LED 0805 (indicator colour is a design choice)"),
    "D3":  (7496834,  "Red LED 0805 (indicator colour is a design choice)"),
    "FB1": (6750922,  "Ferrite bead 220Ω@100MHz 2A 0805"),
    "J4":  (7501262,  "1x4 2.54mm pin header, THT (hand/manual solder)"),
    "L1":  (17236259, "SRN6045HA-100M 10µH — LOW STOCK (17)"),
    "R3":  (7468432,  "10kΩ 0805 ±5%"),
    "R4":  (7471596,  "5.1kΩ 0805 ±0.5% (only in-stock option)"),
    "R10": (7471245,  "2.2kΩ 0805 ±1% — LOW STOCK (49)"),
    "U3":  (6807798,  "USBLC6-2SC6-FS — functional equiv; design's '4SC6' is nonstandard, 2SC6 is the real ST part, same SOT-23-6"),
    # ---- no in-stock match in this jlcparts snapshot ----
    "R1":  (None, "113kΩ 0805 — NO in-stock part at any package in this DB"),
    "R2":  (None, "13kΩ 0805 — none at 0805 (only 0402/1206 in stock)"),
    "R9":  (None, "660Ω 0805 — NO in-stock part at any package in this DB"),
    "J1":  (None, "USB-C TYPE-C-31-M-12 OOS; nearest in-stock: C7431072 'TYPE-C 16PIN 5A 143' — VERIFY footprint before use"),
    "J2":  (None, "JST SH SM04B-SRSS-TB OOS; nearest 1mm SMD 4P: C7430446 ZX-SH1.0-4PWT — VERIFY footprint"),
    "J3":  (None, "JST SH SM04B-SRSS-TB OOS; nearest 1mm SMD 4P: C7430446 ZX-SH1.0-4PWT — VERIFY footprint"),
    "JP1": (None, "C&K PTS810 SMD tact switch — not in stock/absent in this DB"),
    "SW1": (None, "C&K PTS810 SMD tact switch — not in stock/absent in this DB"),
    "U1":  (None, "LMR62014XMF boost — absent in this DB"),
    "U2":  (None, "MIC5504-3.3YM5 LDO — absent in this DB"),
    "U4":  (None, "ESP32-C3-WROOM-02 — only -N16 variant present, stock 0"),
}
SKIP = {"A1", "TP1"}  # logo + test points: not assembled, absent from CPL

def stock_of(lcsc):
    r = DB.execute("SELECT stock,mfr,library_type,preferred FROM jlc_components WHERE lcsc=?", (lcsc,)).fetchone()
    return dict(r) if r else None

bom = list(csv.DictReader(open(HERE / "bom_raw.csv", newline="")))
jlc_rows = [["Comment", "Designator", "Footprint", "LCSC Part #"]]
report = []
for line in bom:
    first = line["Designator"].split(",")[0]
    if first in SKIP:
        report.append((line["Designator"], line["Comment"], "—", "excluded (not assembled: logo/test point)"))
        continue
    lcsc, note = ASSIGN.get(first, (None, "UNHANDLED"))
    part = f"C{lcsc}" if lcsc else ""
    jlc_rows.append([line["Comment"], line["Designator"], line["Footprint"], part])
    if lcsc:
        s = stock_of(lcsc)
        lt = "Basic" if s and s["library_type"] == "base" else ("Preferred" if s and s["preferred"] else "Extended")
        st = f"stock={s['stock']} [{lt}] {s['mfr']}" if s else "??"
        report.append((line["Designator"], line["Comment"], f"C{lcsc}", f"{st}  |  {note}"))
    else:
        report.append((line["Designator"], line["Comment"], "— none —", note))

with open(HERE / "production_files" / "luftctl-bom.csv", "w", newline="") as f:
    csv.writer(f).writerows(jlc_rows)

# report
matched = sum(1 for r in report if r[2].startswith("C"))
unmatched = [r for r in report if r[2] == "— none —"]
print(f"JLCPCB BOM written: {len(jlc_rows)-1} placeable line items, "
      f"{matched} with verified in-stock LCSC, {len(unmatched)} needing manual sourcing.\n")
print(f"{'Designator':18}{'Value':22}{'LCSC':11}Verification (jlcparts 2026-09-24)")
print("-"*130)
for des, val, lcsc, note in report:
    print(f"{des:18}{val:22}{lcsc:11}{note}")
