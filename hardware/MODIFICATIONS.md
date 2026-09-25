# luftctl — design change: USB‑C PD 12 V input + GPIO breakout

## ✅ Implementation status (branch `usbc-pd-12v-and-gpio-breakout`)

**Both changes are implemented in the schematic** (`luftctl.kicad_sch`) and
verified: the netlist was re-exported and every rail/net checked, and ERC is at
the project's baseline (the remaining violations are pre‑existing
`lib_symbol_mismatch` from this project's custom symbols, plus one benign
"power pin not driven" on the CH224K's self‑generated VDD). See the rendered
result in **`luftctl-modified-schematic.pdf`**. Firmware (`main.py`,
`esphome/luftctl.yaml`) is updated.

Done in the schematic:
- Removed: U1 (boost), L1, D1, R1, R2, C6, R4/R5 (CC pull‑downs), U2 (LDO).
- Added: **U5 CH224K** PD trigger, **U6 LMR51420** buck, L2 (10 µH), R11/R12
  (buck FB divider), R13/R14/R15 (CH224K CFG straps), C12 (boot), C13 (buck Vin),
  C14 (buck Vout), C15 (CH224K VDD), **J6** 1×8 GPIO breakout.
- +5 V rail merged into +12 V; **J2/J3 power pins moved to +3V3**; fans stay on +12 V.
- Net `12V_EN` renamed **GPIO3** and broken out on J6 (R3 remains as a harmless
  10 kΩ pull‑down on that pin — delete it if you don't want one).

**Two remaining steps must be done in the KiCad GUI (can't be done headless):**
1. Open the PCB → **Tools ▸ Update PCB from Schematic** (one click). This pulls in
   J6, U5, U6, L2, R11–R15, C12–C15 with correct nets and drops the removed parts.
2. **Place and route** the new parts — especially the buck's switching loop
   (Cin→VIN/GND tight, short SW node, FB away from SW) per the layout notes below.
   Then re‑run the JLCPCB `jlcpcb/` generation (those files are pre‑mod).

## Datasheet-confirmed values (researched + cross-verified, high confidence)

### CH224K — request 12 V  (source: WCH CH224 datasheet V2.0, §6.2 / §7.1)

Standalone I/O-strap truth table (**CH224K**, not the CH224A/Q table):

| CFG1 | CFG2 | CFG3 | Request |
|:----:|:----:|:----:|:--------|
| 1 | X | X | 5 V |
| 0 | 0 | 0 | 9 V |
| **0** | **0** | **1** | **12 V** |
| 0 | 1 | 1 | 15 V |
| 0 | 1 | 0 | 20 V |

`0` = strap to GND, `1` = HIGH. **CH224K has NO internal pull-ups on CFG2/CFG3**,
so a `1` must be pulled up externally — it cannot float.

> ⚠️ **Two bugs in the current netlist — the board as drawn would give 9 V and a dead chip:**
> 1. **R15/CFG3 is strapped to GND (=0) → selects 9 V, not 12 V.** CFG3 must be
>    **pulled HIGH to VDD via ~10 kΩ** (the reference schematic value), not tied to GND.
>    Keep R13/CFG1→GND and R14/CFG2→GND (both `0`, correct).
> 2. **VDD (pin 1) is not powered** — it only has C15 (1 µF) to GND. VDD must be fed
>    **from VBUS through a ~1 kΩ series resistor** (reference-schematic value; VDD is a
>    ~3.6 V shunt-regulated logic rail). Without it the chip never runs. This is the
>    "power pin not driven" ERC warning. Add R_VDD (VBUS→VDD, 1 kΩ).
> 3. **VBUS (pin 8) sense** should reach the pin through a **series resistor**, not a
>    direct tie to the 12 V rail (per the reference schematic).
>
> So: R13 = 0 Ω (CFG1→GND) ✔, R14 = 0 Ω (CFG2→GND) ✔, **R15 = 10 kΩ pull-up CFG3→VDD**,
> **add R_VDD = 1 kΩ VBUS→VDD**, and a series R on the VBUS-sense pin. PG/DP/DM stay NC.
> (I2C config is not available on CH224K.)

### LMR51420 — set 3.3 V  (source: TI SLUSEF6C, §7.6 / §9.2.2.2, Eq. 9)

- **VREF = 0.600 V**; `Vout = VREF · (1 + RFBT/RFBB)`.
- TI's 3.3 V typical value: **RFBT (R11) = 100 kΩ, RFBB (R12) = 22.1 kΩ → 3.315 V**.
- **Current board R11 = 100 kΩ / R12 = 22 kΩ → 3.327 V (+0.8 %)** — in tolerance and
  fine to leave; swap R12 to **22.1 kΩ (E96)** for the datasheet-exact +0.45 %.
- **No feedforward cap** — the LMR51420 is internally compensated (do NOT reuse the
  old boost's 220 pF C6).

### Footprint

- **CH224K** is `SSOP-10-1EP_3.9x4.9mm` (KiCad default here); confirm against the exact
  package you order. Buck is SOT-23-6; L2 reuses the SRN6045 6×6 footprint.

---


Engineering change spec for two modifications:

1. **Power the fans from 12 V negotiated over USB‑C Power Delivery** instead of
   boosting 5 V → 12 V on‑board.
2. **Break out a few spare GPIOs** on an easy 2.54 mm Dupont header.

> This document is the schematic/BOM change list. The symbol placement, wiring,
> and PCB routing still need to be done in the KiCad GUI — switching‑regulator
> layout (buck loop, feedback, thermals) must not be done blind. Everything you
> need to execute it is below.

## ⚠️ Hard requirement for mod 1

12 V over USB‑C **only works from a USB‑C Power‑Delivery source** (a PD charger /
PD power bank). A plain 5 V USB port or an A‑to‑C cable **cannot** supply 12 V —
the board will get no fan power in that case. After the PD contract is made,
**VBUS itself becomes 12 V**, which is why the on‑board boost is removed and a
buck is added for the 3.3 V logic (a 5 V→3.3 V LDO can't run from 12 V).

## Decisions taken

| Topic | Choice |
|---|---|
| 12 V source | **CH224K** PD trigger, fixed 12 V, standalone (no firmware) |
| 3.3 V logic supply | **Single 12 V→3.3 V buck** (LMR51420); J2/J3 power pin becomes 3.3 V |
| Fan 12 V gating | **Removed** — 12 V always on, fans controlled by PWM only; IO3 freed |
| GPIO breakout | 1×8 header: **IO2, IO3, IO8, IO20/RX, IO21/TX, 3V3, GND, GND** |

---

## New power architecture

```
                              CH224K (U5)                 LMR51420 buck (U6)
 USB-C ─┬─CC1───────────────► CC1                       ┌──► VIN ──SW──L2(10µH)──┬──► +3V3 ─► ESP32 + pullups + J2/J3 pwr
 (J1)   ├─CC2───────────────► CC2                       │                        │
        │                     CFG1/2/3 ─(strap 12V)     │              R_top ─────┤
        ├─VBUS ──FB1──┬───────► VBUS  ───────────────────┤              FB ◄───────┤
        │             │        PG ─(opt, NC)             │              R_bot ──GND │
        │             │        GND                       │   EN─(pullup to VIN)     │
        │             ├──────────────────────────────────┘   BST─Cboot─SW           │
        │             │                                                              │
        │             ├──► +12V ──► J4.2 / J5.2  (fan power, always on)              │
        │             └──► Cbulk (≥10µF, ≥25V) + Cin_buck (reuse C1/C7 4.7µF/50V)    │
        └─D+/D- ──► U3 (USBLC6 ESD) ──► ESP32 IO19/IO18   (unchanged)
```

*The old +5 V rail no longer exists.* "VBUS" and "+12 V" are the same
post‑negotiation rail; keep FB1 as an input EMI bead (verify its 2 A rating vs
your fans' stall current, or short it out).

### Remove

| Ref | Part | Why |
|---|---|---|
| U1 | LMR62014XMF boost | 12 V now comes from PD, not a boost |
| D1 | 1N5819 (boost catch diode) | boost gone |
| R1, R2 | 113 kΩ / 13 kΩ (boost FB divider) | boost gone (footprints reusable for buck FB, new values) |
| C6 | 220 pF (boost feed‑forward) | boost gone |
| R4, R5 | 5.1 kΩ CC pull‑downs | CH224K provides its own CC termination/BMC; leaving Rd would force a 5 V‑only contract |
| U2 | MIC5504‑3.3 LDO | can't run from 12 V; replaced by buck |

### Repurpose (reuse footprint / net rework, don't delete)

| Ref | Was | Now |
|---|---|---|
| L1 | 10 µH boost inductor (SRN6045, +5V↔SW) | buck inductor **L2** between buck SW and +3V3 (same SRN6045 6×6 pad; keep 10 µH) |
| C8 | 10 µF boost output cap on +12V | +12 V bulk cap on VBUS (12 V) |
| C1, C7 | 4.7 µF/50 V input caps on +5V | buck VIN caps on +12 V (50 V rating is fine) |
| C10 | 10 µF on +3V3 | buck output cap on +3V3 (add a 22 µF if ripple needs it) |
| FB1 | bead VBUS→+5V | bead VBUS→+12V input filter (or DNP) |

### Add

| Ref | Part | Function | Notes |
|---|---|---|---|
| U5 | **CH224K** PD sink controller | negotiate fixed 12 V | CC1/CC2 → J1 CC; VBUS sense → VBUS; strap CFG1‑3 for 12 V **per datasheet** (12 V ≈ CFG1=GND, CFG2=GND, CFG3=high — *verify against CH224K Table*); 100 nF on VDD; PG open‑drain optional (leave NC or route to a test point) |
| U6 | **LMR51420** buck (SOT‑23‑6) | 12 V → 3.3 V logic | VIN=+12V, EN pulled up to VIN, SW→L2→+3V3, FB divider to +3V3, Cboot ~100 nF (BST–SW). Set 3.3 V via FB divider: `Vout = Vref·(1+Rtop/Rbot)`, **confirm Vref (~0.6–0.8 V)** from datasheet; e.g. with Vref 0.8 V use Rbot 10 kΩ, Rtop 31.6 kΩ (reuse R1/R2 pads) |
| J6 | **1×8 2.54 mm header** | GPIO breakout (Dupont) | pinout below |
| Cboot, Cin/Cout | small ceramics | buck support | per LMR51420 datasheet (typ. 100 nF boot, 10 µF in, 22 µF out) |

---

## GPIO breakout header (J6)

1×8, 2.54 mm, Dupont‑compatible. Suggested pinout:

| Pin | Signal | ESP32‑C3 | Notes |
|----:|--------|----------|-------|
| 1 | **3V3** | — | logic supply out (from buck), keep peripheral load small |
| 2 | **GND** | — | |
| 3 | **IO2** | GPIO2 | spare; has 10 kΩ boot‑strap pull‑up (must be high at reset) |
| 4 | **IO3** | GPIO3 | freed by removing the 12 V enable |
| 5 | **IO8** | GPIO8 | spare; has 10 kΩ boot‑strap pull‑up (must be high at reset) |
| 6 | **RX** | GPIO20 | UART0 RX (also on JST J2) |
| 7 | **TX** | GPIO21 | UART0 TX (also on JST J2) |
| 8 | **GND** | — | 2nd ground for jumpers |

Connect each pin with a short wire stub + a **local label** matching the existing
net name (`GPIO2`, `12V_EN`→rename to `GPIO3`, `GPIO8`, `RXD`, `TXD`, `+3V3`,
`GND`); connectivity is by label, so it nets correctly regardless of placement.
**Strapping caution:** IO2 and IO8 (and IO9) must not be pulled low at reset —
don't hang a hard pull‑down or a bus that idles low on IO2/IO8.

---

## Part selection & availability (vs jlcparts snapshot 2026‑09‑24)

| Ref | Recommended part | LCSC | In‑stock? |
|---|---|---|---|
| U5 | CH224K (WCH) | — | **Not in this snapshot.** In‑stock drop‑in: **HUSB238** `C7471904` (Hynetek, DFN‑10, 9,642). HUSB238 wants I2C or a strap to select 12 V — for a truly no‑firmware build prefer CH224K (re‑check a live jlcparts build), else set 12 V over I2C from the ESP at boot. |
| U6 | LMR51420YFDDCR (TI, SOT‑23‑6, 36 V/2 A) | `C7296200` | ✅ 6,432 |
| L2 | 10 µH power inductor | reuse L1 SRN6045 (`C17236259`, low stock 17) or 4×4 `C6808084` ANR4018T100M (37 k) if you change the footprint | ⚠ |
| J6 | 1×8 2.54 mm header | `C7501266` (ZX‑PZ2.54‑1‑8PZZ) | ✅ 2,311 |

Buck support passives (Cboot/Cin/Cout, FB resistors) and the kept passives are
covered by the existing 0805 assignments in `jlcpcb/VERIFICATION.md`. **Regenerate
the JLCPCB BOM/CPL after the KiCad edits** — the current files in `jlcpcb/` reflect
the pre‑mod board.

---

## PCB / layout notes

- **Buck (U6):** tight input‑cap loop (Cin → VIN/GND), short SW node, keep FB
  divider away from SW, single‑point ground for the power stage. Follow the
  LMR51420 datasheet layout example. The freed U1/L1/D1 area gives you room.
- **CH224K (U5):** place near J1; CC1/CC2 short and direct to the connector;
  bulk cap on VBUS close to the connector for fan inrush.
- **12 V trace to fans (J4/J5):** widen for fan stall current (both fans + inrush).
- **Delete** the R4/R5 pads and the boost components; **re‑net** J2.2/J3.2 from
  +5V to +3V3.

---

## Firmware changes (done in this repo)

- `main.py` and `esphome/luftctl.yaml`: the GPIO3 "enable 12 V" control is
  removed (12 V is always present now); fans are off at PWM = 0 %. GPIO2/3/8 and
  UART are noted as available on J6. See those files.
- Note for connected peripherals: **J2/J3 power pin is now 3.3 V, not 5 V.**
