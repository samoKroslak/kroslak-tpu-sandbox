# Bambu Studio slicer profiles

Three profiles, two materials. Apply per the architecture you're testing.

> Common to all three: drop the 3MF on the build plate → right-click "Repair model" → apply profile → slice. Watch first 5 minutes of the print in person — TPU prints fail at the first layer if at all.

---

## Profile 1 — TPU 85A baseline (the material you already own)

Use for: validating the workflow end-to-end before the Foamy spool arrives.

### Filament profile (custom, duplicate of Bambu TPU 95A HF)

| Setting | Value | Why |
|---|---|---|
| Nozzle temp (initial layer) | 240°C | Bambu wiki recommendation for first-layer adhesion on 85A |
| Nozzle temp (other layers) | 225°C | Bambu wiki tuned default — do not override |
| Bed temp | 30–35°C | Higher bed makes TPU stick *too* well to PEI; you'll tear parts |
| Cooling fan | 30% after layer 3 | Keeps geometry crisp without stiffening TPU surface |
| Max volumetric speed | 5 mm³/s | Hard cap. Do not raise. |
| Retraction length | 0.8 mm | Bigger retractions skip the extruder gear on soft TPU |
| Retraction speed | 25 mm/s | |
| Z-hop | 0.4 mm | Prevents head dragging across soft tops |
| Filament density | 1.21 g/cm³ | For accurate mass estimates |
| Flow Dynamics Calibration | OFF | Bambu's preset is already tuned; calibration breaks it |

### Process profile

| Setting | Value | Why |
|---|---|---|
| Layer height | 0.32 mm | 0.6 nozzle handles this fine; cuts print time vs 0.2 |
| Initial layer height | 0.36 mm | Extra material for first-layer squish |
| Line width — outer wall | 0.6 mm | Match nozzle |
| Line width — inner wall | 0.65 mm | |
| Line width — initial layer | 0.7 mm | |
| Speeds — outer wall | 20 mm/s | Slow is your friend with soft TPU |
| Speeds — inner wall | 25 mm/s | |
| Speeds — initial layer | 15 mm/s | |
| Speeds — travel | 80 mm/s | Lower than default to avoid jerking soft TPU |
| **Wall loops** | **2** | **Closes the lattice surface for fabric to drape on; minimal stiffness add** |
| **Top shell layers** | **0** | **Leave gyroid open — it IS the structure** |
| **Bottom shell layers** | **3** | **Captures the 1mm solid base built into the geometry** |
| **Sparse infill density** | **0%** | **The gyroid IS the infill** |
| Detect thin walls | ON | Single-line gyroid walls need this |
| Brim — type | outer brim only | |
| Brim — width | 5 mm | TPU sticks well but lattice-base touches plate at many small points |

### Printer-side pre-flight

- Confirm 0.6 mm hardened steel hotend installed (P2S/H2 series, not P1)
- Set filament source: **external spool** (not AMS)
- Disable: filament loading test, extrusion calibration, vibration calibration (all fail on soft TPU and abort prints)
- Use **Bambu TPU 85A** as the material when prompted (not generic)

---

## Profile 2 — FilaFlex Foamy, Architecture C (production / under-fabric)

Use for: the parts that will be wrapped in Dacron + fabric and delivered as Krošlák products. Maximum foaming throughout. The geometry handles all the comfort; the fabric is the visible/touch surface.

Start from Profile 1 and change:

| Setting | Profile 1 value | Profile 2 (Foamy C) value | Why |
|---|---|---|---|
| Nozzle temp (initial layer) | 240°C | 250°C | Foamy needs higher temp to foam; first layer hottest for adhesion |
| Nozzle temp (other layers) | 225°C | **245°C** | **Triggers full foaming; ~60A density across the part** |
| **Flow ratio** | 1.00 | **0.65** | **Material expands ~1.5× when foamed; reduce flow to match** |
| Filament density | 1.21 g/cm³ | 0.85 g/cm³ | Foamed mass per cm³; for accurate estimates |
| Outer wall speed | 20 mm/s | 18 mm/s | Foamy is more sensitive to speed than 85A |
| Wall loops | 2 | 2 | Same — fabric cover doesn't need a thick skin |

Everything else stays the same as Profile 1.

**Critical:** Recreus profiles for the P2S are downloadable from recreus.com (per their product page). Pull those as a sanity check against the values above before the first print — they may have updated parameters since this doc was written.

---

## Profile 3 — FilaFlex Foamy, Architecture A (showroom / integral skin)

Use for: exposed-surface parts. Master & Master pitch pieces, Salone exhibition samples, From Sarfia premium pieces. The print itself has a denser smoother skin and a foamed soft core — no fabric needed.

The principle: print **outer walls at 215°C** (no foaming, ~82A skin) and **infill at 245°C** (max foaming, ~60A core). The transition is gradient, not abrupt — there's no drumhead effect.

### How to set this up in Bambu Studio

Bambu Studio doesn't expose per-feature temperature in the GUI. Two ways to achieve it:

**Method A — single-temperature compromise (fastest to try):**
Run the whole print at **230°C**. You get partial foaming (~70A core) and a slightly denser surface from the outer walls being last-printed and slowest-cooled. Less dramatic than true Architecture A but zero G-code surgery. Worth trying first as a baseline.

**Method B — G-code temperature injection per feature (the real Architecture A):**
1. Start from Profile 2 (Foamy C) settings
2. Set base temperature to 245°C (foamed core)
3. Add this to **Filament Settings → Custom G-code → "Change filament G-code"** (so it runs at every layer):

```gcode
; Architecture A — denser walls, foamed core
; Drop temp before outer walls, raise before infill
M104 S215 ; will be overridden per feature below
```

4. Then in **Process → Others → "Per-object G-code"** insert before the outer wall block:
   `M104 S215`
5. And before the infill block:
   `M104 S245`

This is fiddly the first time. Alternative: post-process the sliced G-code with a script that finds `; FEATURE: Outer wall` and `; FEATURE: Sparse infill` comment lines and inserts `M104` commands. Claude Code can write that post-processor in 50 lines if you ask it to.

**Method C — slicer profile fork (cleanest long-term):**
There's an open-source Bambu Studio fork called OrcaSlicer that exposes per-feature temperatures in the GUI. If you do a lot of Architecture A prints, switching to OrcaSlicer for Foamy work eliminates the G-code surgery entirely. Otherwise stay on Bambu Studio.

### What to expect from Architecture A

- Surface should be visibly smoother and slightly stiffer than the foamed core
- Cross-section (cut a sample with a sharp knife) shows dense skin → foamed cells → dense skin
- Surface durability is meaningfully higher than Profile 2 (denser skin resists abrasion)
- Compression feel under your forearm should be nearly identical to Profile 2 (the core is what compresses, the skin just stretches with it)

If the skin feels stiff or you get a drumhead effect, your wall temp is too low or wall count is too high. Drop wall loops to 1, or raise wall temp to 220°C.

---

## When to use which profile

| Situation | Profile |
|---|---|
| Validating workflow with TPU 85A you already own | Profile 1 |
| First Foamy print, learning the material | Profile 2 (full foaming) |
| Production parts going into Krošlák sofas under fabric | Profile 2 |
| Parts you'll hand to Master & Master with no fabric over them | Profile 3 |
| Salone / Meble Polska booth samples, Riabič or Marek collaboration pieces | Profile 3 |
| From Sarfia premium D2C pieces | Profile 3 (with optional silicone coating on top — see CLAUDE.md Architecture B) |
