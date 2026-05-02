# Slicer fragmentation analysis — diagnosis and working config for May 7 print

**Date:** 2026-05-03
**Status:** Diagnosed; working configuration produced; CLAUDE.md updated

---

## TL;DR

The gyroid generator was producing meshes whose walls (0.78–0.89 mm) fell below the slicer's connected-polygon threshold (~1.0 mm on a 0.6 mm nozzle), so per-layer cross-sections fragmented into **2600+ disconnected polygons** instead of one continuous wall. The slicer wasn't broken — the geometry was unprintable as designed. **Fix: keep all gyroid walls ≥ 1.2 mm.** Walls = `t · L / π` for sheet gyroid; the script's previous `t_top` minimum of 0.15 mm produced ~0.4 mm walls, far too thin. Two ready-to-print files generated for Thursday.

## Diagnosis

### What the user observed
- Sliced [armrest_single_test_h5_L5-8_t0.5-0.35_grad1.5.3mf](../out/armrest_single_test_h5_L5-8_t0.5-0.35_grad1.5.3mf) (walls 0.78–0.89 mm) in OrcaSlicer with `infill=0%, top_shell=0, bottom_shell=3, wall_loops=2`
- Slicing completed in 1 h 32 m wall-clock (the user thought it was hung; it was just slow)
- Result: 33.6% travel time, only 10.69 g of filament for an 18.9 cm³ part, preview showed **thousands of disconnected dots** instead of continuous walls

### Quantitative measurement
Sliced the mesh in trimesh at multiple z heights and counted distinct closed polygons in each layer cross-section:

| z (mm) | Thin walls (failing) | Thick walls (working) | New safe matrix |
|---|---:|---:|---:|
| 1.5 | **2600** | 57 | 128 |
| 2.0 | 2112 | 1 | — |
| 2.5 | 2085 | 2 | — |
| 3.0 | 2006 | 1 | 72 |
| 3.5 | (failed to recover) | 1 | — |
| 4.0 | 1626 | 22 | 24 |
| 4.5 | 1435 | 37 | 42 |

The thin-walls file produced **2000+ disconnected polygons per layer.** Each one needs its own walls computed and the print head has to travel between every single one. That's the 33.6% travel time, the dot-pattern preview, and the 1 h 32 m slicing time.

The thick-walls file produced **1–2 connected polygons per layer in most layers** — the gyroid sheet's cross-section forms a single closed loop. Slicer just walks it.

### Root cause
Sheet gyroid walls of thickness `w = t · L / π`. When `w` falls below ~1.0 mm on a 0.6 mm nozzle (line width 0.63 mm), the gyroid's cross-section curves don't connect to each other — the slicer sees thousands of isolated thin wall segments and either:
1. Generates per-segment perimeter offsets that produce zero usable extrude path → fragmented dots, OR
2. Triggers "Detect thin walls" centerline tracing per segment → continuous dots-on-segments output with massive travel between

The threshold is empirical (~1.0 mm) rather than the theoretical 2× line_width (1.26 mm) — the gyroid topology happens to bridge between adjacent cells slightly below 1.26 mm, which means walls of 1.05–1.20 mm slice as single connected polygons even though each individual wall section is below 2× line_width.

## Printable envelope (0.6 mm hardened steel nozzle)

Wall thickness `w = t · L / π`. Empirical thresholds from polygon-count sweeps:

| Wall thickness | Slicer behavior | Recommendation |
|---|---|---|
| ≥ 1.4 mm | Clean: ~50 polygons/layer max | **Safe** — primary target for Foamy |
| 1.2–1.4 mm | OK: ~100–150 polygons/layer | Acceptable |
| 1.05–1.20 mm | Marginal: connected but thin walls | Avoid for production |
| < 1.0 mm | Fragmented: 1000s of polygons/layer | **Unprintable** as gyroid |

For variable density across z, both `t_bottom · L_bottom / π` and `t_top · L_top / π` must clear ~1.2 mm. This bounds `t_min` from below: `t ≥ 1.2 · π / L`.

| L (mm) | min t for printable wall | volume fill at min t (~2t) |
|---|---:|---:|
| 6 | 0.63 | 126% (saturated, ~solid) |
| 8 | 0.47 | 94% (very dense) |
| 10 | 0.38 | 76% (dense) |
| 12 | 0.31 | 62% (medium) |
| 14 | 0.27 | 54% (open) |

Larger cells let you get sparser fills while keeping walls thick. For "soft top" parts, lean toward `L_top ≥ 10 mm`.

## Recommended configuration for May 7 print

Two ready-to-print files generated. Pick one.

### Option A — single bun (safest, simplest) ⭐ recommended

[`ready_for_print/foamy_thursday_single.3mf`](../ready_for_print/foamy_thursday_single.3mf)

- Single 100 × 90 × 5 mm bun
- `L = 6 → 10 mm`, `t = 0.7 → 0.45`, `gradient_power = 1.5`
- Walls: 1.34 / 1.43 mm — comfortably above threshold
- Fill: 70% bottom → 45% top (firm-ish base, soft top)
- 355k faces, 0 non-manifold edges, max 57 polygons/layer
- ~24 cm³, ~20 g foamed Foamy

Use this for the first Foamy shakedown. One part, validates printer + filament + geometry pipeline. Press it after print, see how Foamy behaves.

### Option B — 4-bun comparison plate (more data, slightly more risk)

[`ready_for_print/foamy_thursday_matrix.3mf`](../ready_for_print/foamy_thursday_matrix.3mf)

- 4 buns in 2×2 layout: heights (3, 5 mm) × densities (dense, sparse)
- Dense buns: `L = 6/9, t = 0.65/0.45` → walls 1.24/1.29 mm, fill 65%/45%
- Sparse buns: `L = 8/12, t = 0.50/0.32` → walls 1.27/1.22 mm, fill 50%/32%
- 994k faces, 4 non-manifold edges, max 128 polygons/layer
- ~74 cm³, ~63 g foamed Foamy

Use this if you want comparison data in one print. All four buns share the geometric design but differ in height and density — direct A/B/C/D feel comparison.

### Slicer settings (apply in OrcaSlicer or Bambu Studio)

Filament: custom profile based on Bambu TPU 85A, modified per [slicer-profiles.md](../slicer-profiles.md) Profile 2 (Foamy Architecture C):
- Nozzle temp other layers: **245 °C**
- Nozzle temp initial layer: 250 °C
- Bed temp: 32 °C
- Flow ratio: **0.65**
- Filament density: 0.85 g/cm³
- Outer wall speed: 18 mm/s

Process settings:
- Layer height: **0.32 mm**, initial 0.36 mm
- Wall loops: **2**
- Top shell layers: **0** (gyroid is the structure)
- Bottom shell layers: **3** (anchors the geometric base)
- Sparse infill density: **0%** (the gyroid IS the infill — critical)
- Brim: outer only, **5 mm width**
- Detect thin walls: leave as default (won't trigger with our wall thicknesses)

Printer:
- Bambu Lab P2S
- 0.6 mm hardened steel nozzle
- External spool (not AMS)
- Disable filament loading test, extrusion calibration, vibration calibration in printer prompts (all abort soft-TPU prints)
- Flow Dynamics Calibration: **OFF** (Device → Calibration)

## How to print on Thursday

Pre-flight (do the night before):
1. Pre-dry the Recreus FilaFlex Foamy spool **8 h @ 50 °C** in the Sunlu S2 dryer
2. Confirm 0.6 mm hardened steel hotend installed (P2S/H2 series)
3. Verify the AMS is flipped back (TPU prints from external spool)
4. Confirm dryer mounted above printer (Henryk's mount)

Day of:
5. Open `ready_for_print/foamy_thursday_single.3mf` in OrcaSlicer
6. Apply the slicer settings above (or save as a profile for reuse)
7. Slice — should complete in **under 2 minutes** (the failing file took 92 minutes; that's your sanity check)
8. Inspect preview: walls should be **continuous closed loops**, not dots. Travel % should be **< 15%**. If you see dots, something's wrong with the file or settings — don't print.
9. Move filament to external spool, set Sunlu dryer to **45 °C** running during print
10. Send to printer; **stay in person for the first 5 layers** (~5 minutes). TPU prints either succeed or fail at the first layer.

Success criteria for the print:
- First layer adheres (5 mm brim helps)
- Walls visibly extruded as continuous lines, not dots
- Foamed surface texture visible (dimpled/spongy looking)
- Part feels foam-like under finger pressure

If the print succeeds, this validates: the geometry pipeline, the foaming filament behavior at 245 °C, the slicer settings, and the printer setup. The next iteration adds the surface treatment test (skin/no-skin per region) and refines density gradients based on what felt right.

## Updates made to the codebase

- **`generate.py`**: Updated `ArmrestParams` defaults to safe wall thicknesses. Added a `min_wall_check` warning when generated walls fall below 1.0 mm.
- **`CLAUDE.md`**: Revised the Parameter Reference section. The previous practical ranges (`t_top` minimum 0.15) produced unprintable meshes — replaced with empirically-validated minimums. Added a "Slicer-printable envelope" subsection.
- **`ready_for_print/foamy_thursday_single.3mf`**: Single-bun shakedown print, validated geometry.
- **`ready_for_print/foamy_thursday_matrix.3mf`**: 4-bun comparison plate, all walls ≥ 1.2 mm.

## Open questions / risks

1. **Polygon count vs slicer behavior is empirical** — the 1.0 mm threshold was determined by mesh cross-section analysis, not by actual slicing in OrcaSlicer. The new files may still need light cleanup if OrcaSlicer's behavior differs from my predictions. Mitigation: slice and inspect preview before printing.

2. **Foamy at 245 °C may behave differently than expected** — first time printing foaming TPU on this rig. Surface texture, dimensional accuracy, foam consistency are all unknowns. Mitigation: print the single bun first (less material wasted if it goes wrong).

3. **Wall thickness limits density range** — the 1.2 mm wall floor caps how sparse we can go. Achievable fill range with safe walls is roughly 30–80% (vs the previous "design" range of 15–80%). Soft comfort zones below 30% fill are not currently achievable on this nozzle. Future: 0.4 mm nozzle could go finer, but Bambu wiki forbids 0.4 mm with 85A and softer TPU.

4. **Surface treatment (skin vs no-skin) deferred** — the original test design included a skin region on 1/3 of each bun. The skin's t-boost (t=2.0) creates abrupt geometry transitions that compounded the slicer's troubles. After this baseline print, surface treatment can be re-introduced once we know the slicer-clean baseline works.

5. **3 mm height parts have a thin gradient zone** — only 2 mm above the 1 mm base. The cells barely express vertically. The 3 mm buns may feel less differentiated from each other than the 5 mm buns. If so, drop 3 mm from future iterations.

## Reproducibility

To regenerate either file from the script:

```bash
# Single bun
python generate.py --height 5 --L-bottom 6 --L-top 10 --t-bottom 0.7 --t-top 0.45 \
    --gradient 1.5 --voxel 0.5 --density 0.85 \
    --name foamy_thursday_single --target-faces 50000 --out-dir ready_for_print

# 4-bun matrix
python generate.py --thin-matrix --density 0.85 --out-dir ready_for_print
# (after generate.py defaults are updated; otherwise see the script's
# thin_skin_matrix_plate function for the exact variant table)
```
