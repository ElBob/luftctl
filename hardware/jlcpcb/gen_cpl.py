#!/usr/bin/env python3
"""Generate the JLCPCB CPL (placement) file from kicad-cli pos output,
applying JLCPCB rotation/offset corrections.

Replicates the exact top-layer logic of matthewlai/JLCKicadTools
cpl_fix_rotations.py:  rotation = (kicad_rot + correction) % 360,
posx += offset_x, posy += offset_y, with the LAST matching regex winning.
All luftctl placements are top-layer, so bottom-layer handling is omitted
(and asserted against).
"""
import csv, re
from pathlib import Path

HERE = Path(__file__).parent
POS  = HERE / "pos_raw.csv"
DB   = Path("/tmp/rotations_source.csv")
OUT  = HERE / "production_files" / "luftctl-top-pos.csv"

# ---- load rotation DB (pattern -> (rot, dx, dy)) in file order ----------
db = []
with open(DB, newline="") as f:
    r = csv.reader(f)
    next(r)  # header
    for row in r:
        if not row or not row[0].strip():
            continue
        pat = re.compile(row[0])
        rot = int(row[1])
        dx  = float(row[2]) if len(row) > 2 and row[2].strip() else 0.0
        dy  = float(row[3]) if len(row) > 3 and row[3].strip() else 0.0
        db.append((pat, rot, dx, dy))

# ---- process pos file ----------------------------------------------------
rows_out = [["Designator", "Mid X", "Mid Y", "Layer", "Rotation"]]
log = []
with open(POS, newline="") as f:
    for rec in csv.DictReader(f):
        ref  = rec["Ref"]
        pkg  = rec["Package"]           # footprint name, no lib prefix
        side = rec["Side"].strip()
        assert side == "top", f"{ref}: unexpected side {side} (bottom logic not implemented)"
        x    = float(rec["PosX"])
        y    = float(rec["PosY"])
        rot  = float(rec["Rot"])

        match = None
        for pat, r_, dx, dy in db:      # last match wins (as in the tool)
            if pat.match(pkg):
                match = (pat.pattern, r_, dx, dy)
        if match:
            _, corr, dx, dy = match
            new_rot = (rot + corr) % 360
            x += dx; y += dy
            log.append((ref, pkg, rot, corr, new_rot, dx, dy, match[0]))
        else:
            new_rot = rot % 360
            log.append((ref, pkg, rot, 0, new_rot, 0.0, 0.0, "(none)"))

        rows_out.append([ref, f"{x:.4f}", f"{y:.4f}",
                         "Top", f"{new_rot:.4f}"])

OUT.parent.mkdir(parents=True, exist_ok=True)
with open(OUT, "w", newline="") as f:
    csv.writer(f).writerows(rows_out)

# ---- report --------------------------------------------------------------
print(f"Wrote {OUT}  ({len(rows_out)-1} placements)\n")
print(f"{'Ref':6}{'Footprint':52}{'kicad':>7}{'corr':>6}{'->new':>7}  pattern")
print("-"*110)
for ref, pkg, rot, corr, new, dx, dy, pat in log:
    flag = "  <== CORRECTED" if corr else ""
    off  = f" +off({dx},{dy})" if (dx or dy) else ""
    print(f"{ref:6}{pkg[:50]:52}{rot:7.0f}{corr:6}{new:7.0f}  {pat}{off}{flag}")
