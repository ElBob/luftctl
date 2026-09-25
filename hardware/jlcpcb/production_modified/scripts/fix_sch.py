#!/usr/bin/env python3
"""CH224K corrections in luftctl.kicad_sch:
 - R15: value 0Ω->10kΩ, pin2 net GND->VDD_CH (makes CFG3 a pull-up to VDD => 12V)
 - add R16: 1kΩ from VBUS to VDD_CH (powers CH224K VDD rail)"""
import re, uuid
F="/Users/robert.bloom/git/luftctl/hardware/luftctl.kicad_sch"
s=open(F).read()
def u(): return str(uuid.uuid4())

# 1) R15 value 0Ω -> 10kΩ (instance + symbol_instances)
assert s.count('"Value" "0Ω" (id 1) (at 62.53 200.89 0)')==1
s=s.replace('"Value" "0Ω" (id 1) (at 62.53 200.89 0)','"Value" "10kΩ" (id 1) (at 62.53 200.89 0)')
assert s.count('(reference "R15") (unit 1) (value "0Ω")')==1
s=s.replace('(reference "R15") (unit 1) (value "0Ω")','(reference "R15") (unit 1) (value "10kΩ")')

# 2) R15 pin2 label GND -> VDD_CH (CFG3 pull-up to VDD)
assert s.count('(global_label "GND" (shape input) (at 49.53 201.93 180)')==1
s=s.replace('(global_label "GND" (shape input) (at 49.53 201.93 180)',
            '(global_label "VDD_CH" (shape input) (at 49.53 201.93 180)')

# 3) add R16 (1kΩ, VBUS->VDD_CH) at (25,210); pins pin1=(25,207.46) pin2=(25,212.54)
X,Y=25.0,210.0
r16_uuid=u(); p1=u(); p2=u()
FP="Resistor_SMD:R_0805_2012Metric_Pad1.20x1.40mm_HandSolder"
r16=f'''  (symbol (lib_id "Device:R_Small") (at {X} {Y} 0) (unit 1)
    (in_bom yes) (on_board yes)
    (uuid {r16_uuid})
    (property "Reference" "R16" (id 0) (at {X+13} {Y-1} 0)
      (effects (font (size 1.27 1.27)) (justify left))
    )
    (property "Value" "1kΩ" (id 1) (at {X+13} {Y+1.5} 0)
      (effects (font (size 1.27 1.27)) (justify left))
    )
    (property "Footprint" "{FP}" (id 2) (at {X} {Y} 0)
      (effects (font (size 1.27 1.27)) hide)
    )
    (property "Datasheet" "~" (id 3) (at {X} {Y} 0)
      (effects (font (size 1.27 1.27)) hide)
    )
    (pin "1" (uuid {p1}))
    (pin "2" (uuid {p2}))
  )
'''
IREF="${INTERSHEET_REFS}"
def lbl(net,x,y):
    return f'''  (global_label "{net}" (shape input) (at {x} {y} 180) (fields_autoplaced)
    (effects (font (size 1.27 1.27)) (justify right))
    (uuid {u()})
    (property "Intersheet References" "{IREF}" (id 0) (at {x-1} {y} 0)
      (effects (font (size 1.27 1.27)) (justify right) hide)
    )
  )
'''
labels=lbl("VBUS",X,Y-2.54)+lbl("VDD_CH",X,Y+2.54)
s=s.replace("  (sheet_instances", r16+labels+"\n  (sheet_instances")
s=s.replace("  (symbol_instances\n",
            "  (symbol_instances\n"+f'    (path "/{r16_uuid}"\n      (reference "R16") (unit 1) (value "1kΩ") (footprint "{FP}")\n    )\n')

open(F,"w").write(s)
print("R15 -> 10kΩ pull-up CFG3->VDD_CH; added R16 1kΩ VBUS->VDD_CH")
