#!/usr/bin/env python3
"""Produce JLCPCB assembly BOM + rotation-corrected CPL for the MODIFIED board."""
import csv, re
from pathlib import Path
OUT = Path("/Users/robert.bloom/git/luftctl/hardware/jlcpcb/production_modified")

# value/comment -> (LCSC, note).  ""/None = no in-stock match (manual sourcing)
ASSIGN = {
 "4.7µF": ("C7472969","4.7uF X5R 50V"), "1µF": ("C6641028","1uF X7R 100V"),
 "100nF": ("C7503487","100nF X7R 100V"), "10µF": ("C16194907","10uF X7S 25V"),
 "22µF": ("C7432777","22uF 0805"),
 "USR": ("C7496834","Red LED 0805"), "PWR": ("C7496834","Red LED 0805"),
 "220ΩZ": ("C6750922","Ferrite 220Ω@100MHz 2A"),
 "PWM Fan": ("C7501262","1x4 2.54mm header THT"), "Conn_01x08": ("C7501266","1x8 2.54mm header THT (J6 breakout)"),
 "10kΩ": ("C7468432","10k 0805 5%"), "100kΩ": ("C7319379","100k 0805 (buck FB top)"),
 "22kΩ": ("C6457890","22k 0805 (buck FB bot)"), "0Ω": ("C7468447","0Ω jumper (CH224K CFG straps*)"),
 "2.2kΩ": ("C7471245","2.2k 0805 - LOW STOCK"),
 "10µH": ("C17236259","SRN6045HA-100M 10µH - LOW STOCK (buck inductor)"),
 "LMR51420YFDDCR": ("C7296200","LMR51420 36V/2A buck"),
 "USBLC6-4SC6": ("C6807798","USBLC6-2SC6-FS - functional equiv, verify pinout"),
 # ---- no in-stock match in this jlcparts snapshot ----
 "CH224K": (None,"PD trigger - not in this DB; in-stock equiv HUSB238 C7471904 (I2C/strap-config)"),
 "ESP32-C3-WROOM-02": (None,"main module - only -N16 variant present, stock 0"),
 "USB_C_Receptacle_USB2.0": (None,"HRO TYPE-C-31-M-12 OOS; nearest C7431072 'TYPE-C 16PIN 5A 143' verify FP"),
 "UART": (None,"JST SH SM04B-SRSS-TB OOS; nearest C7430446 verify FP"),
 "I2C": (None,"JST SH SM04B-SRSS-TB OOS; nearest C7430446 verify FP"),
 "Bootloader": (None,"C&K PTS810 SMD tact switch - absent in DB"),
 "Reset": (None,"C&K PTS810 SMD tact switch - absent in DB"),
 "660Ω": (None,"660Ω 0805 - no in-stock part in DB"),
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
    rows.append([val,des,fp,f"C{lcsc}" if isinstance(lcsc,str) and lcsc.startswith("C") else (lcsc or "")])
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
