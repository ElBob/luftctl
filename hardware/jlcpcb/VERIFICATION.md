# luftctl — JLCPCB assembly files & parts verification

Generated 2026-09-24 from `hardware/luftctl.kicad_pcb` / `.kicad_sch`
(KiCad 6 project) using `kicad-cli` 10.0.6.

## Output files (`production_files/`)

| File | Purpose |
|------|---------|
| `luftctl-bom.csv` | JLCPCB BOM (`Comment, Designator, Footprint, LCSC Part #`) |
| `luftctl-top-pos.csv` | JLCPCB CPL / placement (`Designator, Mid X, Mid Y, Layer, Rotation`), **rotation-corrected**, mm |
| `luftctl-gerber.zip` | Single-board Gerbers + PTH/NPTH Excellon drill (RS-274X, mm, aux origin) |

Non-assembly items are excluded from both BOM and CPL: `A1` (silk logo) and
`TP1–TP4` (test-point THT pads). All 36 placed parts are on the **Top** layer.

## Parts verification against the jlcparts database

Verified against the canonical jlcparts SQLite snapshot
(`yaqwsx.github.io/jlcparts/data/cache.*`), downloaded 2026-09-24; the snapshot's
`fetched_at` timestamps span 2026-09-14 → 2026-09-24. "In stock" = `stock > 0`.

> ⚠️ **Snapshot caveat.** This particular jlcparts build is sparse: every LCSC
> code is ≥ C6374508 (no classic low C-numbers), the companion `lcsc_components`
> table is empty, and only ~1,500 resistors and ~1,500 capacitors are in stock
> across the whole catalog. Classic JLC "Basic" parts (e.g. C1525, ESP32-C3
> C2934569) are entirely absent. As a result several perfectly ordinary parts
> show **no in-stock match in this DB** — that reflects the snapshot, not
> necessarily real-world JLCPCB availability. Re-verify against a live jlcparts
> build before ordering. All library types resolved to "Extended" in this snapshot.

### 15 line items with a verified in-stock LCSC match

| Designator | Value | LCSC | MPN | Stock | Notes |
|---|---|---|---|---|---|
| C1,C7 | 4.7µF | C7472969 | HGC0805R5475K500NSLJ | 350,459 | X5R 50V |
| C3,C4 | 1µF | C6641028 | 08051C105K4T2A | 11,844 | X7R 100V |
| C5,C9,C11 | 100nF | C7503487 | CGA0805X7R104K101KT | 55,238 | X7R 100V |
| C6 | 220pF | C7393918 | TCC0805COG221J501BT | 13 | C0G 500V — **low stock**, only option |
| C8,C10 | 10µF | C16194907 | CL21Y106KABVPNE | 3,824 | X7S 25V (adequate for 12V rail) |
| D1 | 1N5819 | C6562211 | 1N5819W SL | 694 | Schottky, SOD-123 |
| D2 | USR | C7496834 | P2-0805R1TS2 | 861,815 | Red LED 0805 — colour is a design choice |
| D3 | PWR | C7496834 | P2-0805R1TS2 | 861,815 | Red LED 0805 — colour is a design choice |
| FB1 | 220ΩZ | C6750922 | BBPY00201209221Y00 | 2,895 | Ferrite bead 220Ω@100MHz, 2A |
| J4,J5 | PWM Fan | C7501262 | ZX-PZ2.54-1-4PZZ | 39,729 | 1×4 2.54mm header, THT (manual solder) |
| L1 | 10µH | C17236259 | SRN6045HA-100M | 17 | **Low stock**; SRN6045 family per design |
| R3,R6,R7,R8 | 10kΩ | C7468432 | FRQ0805J103 | 28,237 | 0805 ±5% |
| R4,R5 | 5.1kΩ | C7471596 | TE05H5101DT | 470 | 0805 ±0.5% — only option (USB-C CC pulldowns) |
| R10 | 2.2kΩ | C7471245 | FRQ0805F2201 | 49 | 0805 ±1% — **low stock** |
| U3 | USBLC6-4SC6 | C6807798 | USBLC6-2SC6-FS | 1,269 | **Functional equiv.** The schematic's "USBLC6-**4**SC6" is nonstandard; ST's real part is USBLC6-**2**SC6 (same SOT-23-6 USB ESD array). Verify pinout. |

### 11 line items with NO in-stock match in this snapshot (need manual sourcing)

| Designator | Value | Why | Suggested next step |
|---|---|---|---|
| R1 | 113kΩ | No in-stock 0805 (none at any package in this DB) | Source 113k 0805 1%, or split/adjust the feedback divider |
| R2 | 13kΩ | No in-stock **0805** (only 0402/1206 in stock) | Source 13k 0805 |
| R9 | 660Ω | No in-stock 0805 (none at any package in this DB) | 660Ω is unusual; consider 649Ω(E96)/680Ω if the LED current allows |
| J1 | USB-C `TYPE-C-31-M-12` | Exact HRO part OOS | Nearest in-stock 16-pin Type-C: **C7431072** "TYPE-C 16PIN 5A 143" — **verify footprint/pads** vs `USB_C_Receptacle_HRO_TYPE-C-31-M-12` before use |
| J2 | UART (JST SH SM04B-SRSS-TB) | OOS | Nearest 1.0mm 4P SMD: **C7430446** ZX-SH1.0-4PWT — verify footprint |
| J3 | I2C (JST SH SM04B-SRSS-TB) | OOS | same as J2 |
| JP1 | Bootloader (PTS810) | C&K PTS810 SMD tact switch absent | Source a PTS810-compatible SMD tact switch |
| SW1 | Reset (PTS810) | same as JP1 | same |
| U1 | LMR62014XMF | TI boost converter absent | Source LMR62014 (SOT-23-5) |
| U2 | MIC5504-3.3YM5 | Microchip 3.3V LDO absent | Source MIC5504-3.3 (SOT-23-5) |
| U4 | ESP32-C3-WROOM-02 | Only `-N16` variant present, **stock 0** | Source the module (main IC) — critical |

## Placement rotation corrections

Corrections applied per the de-facto standard database
(`matthewlai/JLCKicadTools` `cpl_rotations_db.csv`). For every top-layer part:
`JLC_rotation = (kicad_rotation + correction) mod 360`, plus any X/Y offset
(none applied here). Last matching regex wins.

**3 footprint types were corrected (7 placements):**

| Footprint | Matched pattern | Correction | Affected |
|---|---|---|---|
| `USB_C_Receptacle_HRO_TYPE-C-31-M-12` | `^USB_C_Receptacle_HRO_TYPE-C-31-M-12*` | **+180°** | J1 (90→270) |
| `SOT-23-5` | `^SOT-23` | **−90°** | U1 (−90→180), U2 (0→270) |
| `SOT-23-6` | `^SOT-23` | **−90°** | U3 (−90→180) |

All other footprints (0805 R/C/L/LED, `D_SOD-123`, `L_Bourns_SRN6045TA`,
`FanPinHeader_1x04`, `SW_SPST_PTS810`) have no entry in the standard DB →
0° correction (KiCad and JLC orientations already agree for 2-pad passives).

**⚠️ Two footprints fall in gaps of the standard DB — verify manually:**

- **`JST_SH_SM04B-SRSS-TB…` (J2, J3):** the DB corrects `JST_GH`/`JST_PH` by
  +180° but has **no `JST_SH` rule**. JST SH parts commonly also need +180°.
  (Moot until an LCSC part is chosen; re-check orientation for the substitute.)
- **`ESP-WROOM-02` (U4):** the DB rule `^ESP32-W`→270° does **not** match this
  footprint's name (`ESP-WROOM-02`, not `ESP32-W…`), so no correction was
  applied. These modules typically need a correction; verify pin-1 orientation
  against the chosen module before ordering.

## Reproduce

```
kicad-cli sch export bom  … luftctl.kicad_sch      # -> bom_raw.csv
kicad-cli pcb export pos  --format csv --units mm --use-drill-file-origin … # -> pos_raw.csv
python3 match.py       # parametric + MPN verification against jlcparts
python3 gen_cpl.py     # rotation-corrected CPL
python3 finalize.py    # JLCPCB BOM + this report's table
kicad-cli pcb export gerbers/drill … # -> gerber/ -> luftctl-gerber.zip
```
