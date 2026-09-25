#!/usr/bin/env python3
"""Improved headless sync: spaced placement (no courtyard overlaps), board
extended to y=92, solid GND pours (ZONE_CONNECTION_FULL) inset 0.5mm from edge.
Gather-then-mutate discipline to dodge the pcbnew SWIG downcast bug."""
import re
import pcbnew as P

BOARD="/Users/robert.bloom/git/luftctl/hardware/luftctl-modified.kicad_pcb"
NET  ="/Users/robert.bloom/git/luftctl/hardware/luftctl.net"
LIBDIR="/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"
mm=P.FromMM

nl=open(NET).read()
comps={}
for m in re.finditer(r'\(comp\s+\(ref "([^"]+)"\)(.*?)(?=\(comp\s+\(ref|\)\s*\(libparts|\Z)', nl, re.S):
    ref=m.group(1); body=m.group(2)
    fpm=re.search(r'\(footprint "([^:]+):([^"]+)"\)', body); vm=re.search(r'\(value "([^"]*)"\)', body)
    if fpm: comps[ref]=(fpm.group(1), fpm.group(2), vm.group(1) if vm else "")
padnet={}
for m in re.finditer(r'\(net\s+\(code "\d+"\)\s+\(name "([^"]*)"\)(.*?)(?=\(net\s+\(code|\)\s*\Z)', nl, re.S):
    for r,pin in re.findall(r'\(ref "([^"]+)"\)\s*\(pin "([^"]+)"\)', m.group(2)):
        padnet[(r,pin)]=m.group(1)
allnets=sorted(set(v for v in padnet.values() if v))

# spaced placement in the new bottom strip (y 78..88); J6 alone near the edge
PLACE={
 "U5":(133,79,0), "U6":(143,79,0), "C13":(150,79,0), "C14":(155,79,0), "C15":(160,79,0), "L2":(172,79,90),
 "R11":(133,83,0),"R12":(138,83,0),"R13":(143,83,0),"R14":(148,83,0),"R15":(153,83,0),"C12":(158,83,0),
 "J6":(145,88,90),
}
REMOVE={"U1","U2","D1","R1","R2","R4","R5","C6","L1"}

b=P.LoadBoard(BOARD)
# --- GATHER (read accessors + FootprintLoad only) ---
kept=[]; remove_list=[]
for f in b.GetFootprints():
    r=f.GetReference()
    if r in REMOVE: remove_list.append(f)
    elif r in comps: kept.append((r,f))
edge_dwgs=[d for d in b.GetDrawings() if d.GetLayerName()=="Edge.Cuts"]
tracks=list(b.GetTracks())
copper_zones=[z for z in b.Zones() if not z.GetIsRuleArea()]
existing_net={n:b.FindNet(n) for n in allnets if b.FindNet(n) is not None}
new_fps=[]
kept_refs={r for r,_ in kept}
for ref,(lib,fpn,val) in comps.items():
    if ref in kept_refs: continue
    fp=P.FootprintLoad(f"{LIBDIR}/{lib}.pretty", fpn)
    assert hasattr(fp,'SetReference'), f"unwrapped {ref}"
    fp.SetReference(ref); fp.SetValue(val)
    x,y,rot=PLACE.get(ref,(130,88,0)); fp.SetPosition(P.VECTOR2I(mm(x),mm(y)))
    if rot: fp.SetOrientationDegrees(rot)
    new_fps.append((ref,fp))
print(f"gather: kept={len(kept)} remove={len(remove_list)} tracks={len(tracks)} "
      f"copperZones={len(copper_zones)} new={len(new_fps)} existNets={len(existing_net)}")

# --- MUTATE (no collection accessors) ---
for f in remove_list: b.Remove(f)
for d in edge_dwgs:  b.Remove(d)
for t in tracks:     b.Remove(t)
for z in copper_zones: b.Remove(z)
netobj=dict(existing_net)
for n in allnets:
    if n not in netobj:
        ni=P.NETINFO_ITEM(b,n); b.Add(ni); netobj[n]=ni
X0,Y0,X1,Y1=125.6,50.0,182.2,92.0
for (ax,ay),(bx,by) in zip([(X0,Y0),(X1,Y0),(X1,Y1),(X0,Y1)],[(X1,Y0),(X1,Y1),(X0,Y1),(X0,Y0)]):
    s=P.PCB_SHAPE(b); s.SetShape(P.SHAPE_T_SEGMENT)
    s.SetStart(P.VECTOR2I(mm(ax),mm(ay))); s.SetEnd(P.VECTOR2I(mm(bx),mm(by)))
    s.SetLayer(P.Edge_Cuts); s.SetWidth(mm(0.1)); b.Add(s)
for ref,fp in new_fps: b.Add(fp)
for ref,fp in kept+new_fps:
    for pad in fp.Pads():
        nm=padnet.get((ref,pad.GetNumber()))
        if nm and nm in netobj: pad.SetNet(netobj[nm])
gnd=netobj["GND"]
for layer in (P.B_Cu,):
    z=P.ZONE(b); z.SetLayer(layer); z.SetNet(gnd); z.SetIsFilled(False)
    z.SetLocalClearance(mm(0.3)); z.SetMinThickness(mm(0.2))
    z.SetPadConnection(P.ZONE_CONNECTION_FULL)   # solid -> no starved thermals
    ps=P.SHAPE_POLY_SET(); ps.NewOutline()
    for (ax,ay) in [(X0+0.5,Y0+0.5),(X1-0.5,Y0+0.5),(X1-0.5,Y1-0.5),(X0+0.5,Y1-0.5)]:
        ps.Append(mm(ax),mm(ay))
    z.AddPolygon(ps.COutline(0)); b.Add(z)
P.SaveBoard(BOARD, b)
print("synced+placed (spaced), saved")
