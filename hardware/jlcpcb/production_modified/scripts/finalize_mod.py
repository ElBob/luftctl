#!/usr/bin/env python3
"""Produce JLCPCB assembly BOM + rotation-corrected CPL for the MODIFIED board."""
import csv, re
from pathlib import Path
OUT = Path("/Users/robert.bloom/git/luftctl/hardware/jlcpcb/production_modified")

# value/comment -> (LCSC, note).  ""/None = no in-stock match (manual sourcing)
ASSIGN = {
 "4.7µF": ("C1779","4.7uF X5R 50V"), "1µF": ("C28323","1uF X7R 100V"),
 "100nF": ("C49678","100nF X7R 100V"), "10µF": ("C15850","10uF X7S 25V"),
 "22µF": ("C45783","22uF 0805"),
 "USR": ("C84256","Red LED 0805"), "PWR": ("C84256","Red LED 0805"),
 "220ΩZ": ("C6750922","Ferrite 220Ω@100MHz 2A"),
 "PWM Fan": ("C7501262","1x4 2.54mm header THT"), "Conn_01x08": ("C7501266","1x8 2.54mm header THT (J6 breakout)"),
 "10kΩ": ("C17414","10k 0805 (pull-ups R3/6/7/8 + CH224K CFG3 pull-up R15)"),
 "1kΩ": ("C17513","1k 0805 (CH224K VDD feed R16)"), "100kΩ": ("C149504","100k 0805 (buck FB top)"),
 "22kΩ": ("C17560","22k 0805 (buck FB bot)"), "0Ω": ("C17477","0Ω jumper - CH224K CFG1/CFG2 straps to GND (R13,R14)"),
 "2.2kΩ": ("C17520","2.2k 0805 - LOW STOCK"),
 "10µH": ("C17236259","SRN6045HA-100M 10µH - LOW STOCK (buck inductor)"),
 "SMF15A": ("C19077509","SMF15A 15V TVS on VBUS (D4)"),
 "LMR51420YFDDCR": ("C7296200","LMR51420 36V/2A buck"),
 "USBLC6-4SC6": ("C6807798","USBLC6-2SC6-FS - functional equiv, verify pinout"),
 # ---- no in-stock match in this jlcparts snapshot ----
 "CH224K": (None,"PD trigger - not in this DB; in-stock equiv HUSB238 C7471904 (I2C/strap-config)"),
 "ESP32-C3-WROOM-02": ("C2934560","ESP32-C3-WROOM-02-N4 PCB-antenna module, 9524 in stock @ JLCPCB, min 1"),
 "USB_C_Receptacle_USB2.0": ("C165948","HRO TYPE-C-31-M-12 in-stock (exact footprint match)"),
 "UART": ("C160404","JST SM04B-SRSS-TB side-entry (J2)"),
 "I2C": ("C160404","JST SM04B-SRSS-TB side-entry (J3)"),
 "Bootloader": ("C720477","XUNPU TS-1088-AR02016 SMD tact, Basic (JP1)"),
 "Reset": ("C720477","XUNPU TS-1088-AR02016 SMD tact, Basic (SW1)"),
 "660Ω": ("C17798","680Ω 0805 Basic (nearest E24 to 660Ω; R9 LED current-limit, ~1.9mA)"),
}
SKIP_FIRST = {"A1","TP1"}  # logo + test points, not assembled

# ---------- BOM ----------
rows=[["Comment","Designator","Footprint","LCSC Part #"]]
report=[]
for line in csv.DictReader(open(OUT/"bom_raw.csv", newline="")):
    des, val, fp = line["Designator"], line["Comment"], line["Footprint"]
    if des.split(",")[0] in SKIP_FIRST:
        report.append((des,val,"—","excluded (logo/test point)")); continue
    lcsc,note = ASSIGN.get(val,(None,"UNHANDLED"))
    rows.append([val,des,fp, lcsc or ""])
    report.append((des,val, (lcsc or "— none —"), note))
csv.writer(open(OUT/"luftctl-mod-bom.csv","w",newline="")).writerows(rows)

# ---------- CPL with rotation corrections ----------
db=[]
for r in csv.reader(open("/tmp/rotations_source.csv")):
    if not r or r[0].startswith('"Footprint') or not r[0].strip():
        if r and r[0].startswith('"Footprint'): continue
    try: db.append((re.compile(r[0]), int(r[1]), float(r[2]) if len(r)>2 and r[2].strip() else 0.0, float(r[3]) if len(r)>3 and r[3].strip() else 0.0))
    except (ValueError, IndexError): pass
cpl=[["Designator","Mid X","Mid Y","Layer","Rotation"]]
corr_log=[]
for rec in csv.DictReader(open(OUT/"pos_raw.csv", newline="")):
    pkg=rec["Package"]; rot=float(rec["Rot"]); x=float(rec["PosX"]); y=float(rec["PosY"])
    side="Top" if rec["Side"].strip()=="top" else "Bottom"
    match=None
    for pat,r_,dx,dy in db:
        if pat.match(pkg): match=(pat.pattern,r_,dx,dy)
    if match and side=="Top":
        _,corr,dx,dy=match; new=(rot+corr)%360; x+=dx; y+=dy
        corr_log.append((rec["Ref"],pkg,rot,corr,new))
    else:
        new=rot%360
    cpl.append([rec["Ref"],f"{x:.4f}",f"{y:.4f}",side,f"{new:.4f}"])
csv.writer(open(OUT/"luftctl-mod-cpl.csv","w",newline="")).writerows(cpl)

# ---------- report ----------
matched=sum(1 for r in rows[1:] if r[3])
print(f"BOM: {len(rows)-1} placeable lines, {matched} with LCSC, {len(rows)-1-matched} to source manually\n")
for des,val,lc,note in report:
    print(f"  {des:16}{val:26}{str(lc):11}{note}")
print(f"\nCPL: {len(cpl)-1} placements. Rotation corrections applied:")
for ref,pkg,rot,corr,new in corr_log:
    print(f"  {ref:5}{pkg[:34]:36} {rot:+.0f} {corr:+d} -> {new:.0f}")
