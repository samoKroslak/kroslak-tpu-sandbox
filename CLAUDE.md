# Krošlák TPU Comfort R&D — Half-Armrest Generator

> Project assignment for Claude Code. Drop this file (and the contents of this folder) into your working directory; Claude Code reads `CLAUDE.md` automatically as project context.

## TL;DR for Claude Code

Build, maintain, and iterate on a Python generator that produces graded sheet-gyroid TPMS lattice cushions as 3MF files for the Bambu Lab P2S. Geometry is parameterised; Samo will vibe-code variants by prompting changes ("smaller cells", "stiffer base", "make a 2×2 comparison plate", "add 8mm corner radius"). The starting script `generate.py` works out of the box. Your job is to evolve it on demand and explain trade-offs in plain language as you go.

## Project context (compressed)

- **Who:** Krošlák, Slovak private-label upholstered furniture manufacturer (~120 employees, ~€8M revenue).
- **Strategic aim:** become the most technologically advanced private-label plant in EU. The 3D-printed comfort programme is one pillar of that.
- **Why printed comfort:** cold foam gives one density per pour. Cut foam gives one density per layer. 3D printing gives **density gradients in three dimensions**, locally tuned to body load patterns. Nobody else in EU private-label upholstery has this capability.
- **Roadmap:**
  1. P2S prototyping → understand the material/geometry design space (NOW)
  2. Office-chair armrest pilot with Master & Master (Slovak premium chair brand)
  3. Lumbar pads, headrests, then full seat inserts in Krošlák sofas
  4. In-house pellet extrusion at factory scale (likely Recreus pellets; Pollen AM Pam or Caracol-class machine, ~€90–150k capex)
- **Premium positioning is intentional and unavoidable.** Printed seat insert material cost is 10–20× cold foam. Path to viability is named-designer pieces, ergonomic chair partners, and From Sarfia premium D2C — not standard volume.

## Hardware reference

### Printer
- Bambu Lab P2S, **0.6mm hardened steel nozzle** (mandatory for TPU 85A and softer; 0.4mm forbidden for ≤85A per Bambu wiki)
- AMS Flipper installed (MakerWorld 1363398) — AMS hinges back when printing TPU
- Henryk's P2S Top Mount (MakerWorld 2070323) holds Sunlu S2 dryer above the printer
- Voltex S2 wedge, bowden-tube variant (MakerWorld 419678) in PETG
- sarad's PTFE adapter, M10 tilt, plate 01 (MakerWorld 589679) in PETG
- **Internal PTFE tube REMOVED** per Bambu wiki — soft TPU free-falls from dryer to extruder
- Textured PEI plate

### Drying
- Sunlu S2 with fan, on top of P2S in Henryk mount
- Pre-dry every TPU spool 8h @ 50°C before first use
- Run dryer @ 45°C continuously during print

### Filaments
| Material | Hardness | State | Notes |
|---|---|---|---|
| Bambu TPU 85A Neon Orange | 85A | In stock | Project baseline; current reference for "comfort" feel |
| Bambu TPU 90A AMS Neon Green | 90A | In stock | Firmer comparison; AMS-compatible (irrelevant since AMS is flipped back) |
| Bambu TPU 95A HF Blue | 95A | In stock | Structural shell zone |
| Fillamentum Flexfill TPU 98A | 98A | In stock | Rigid TPU, structural use |
| **Recreus FilaFlex Foamy Nude** | **82A → 60A foamed** | **INCOMING (~11 May 2026)** | **Primary R&D target. Foaming TPU.** |

### Recreus pellet path (long-term scaling)
Whatever we validate on the P2S in filament form has a 1:1 pellet equivalent at recreus.com/en-en/collections/pellets — Foamy, 60A, 70A, 82A, 95A, SEBS, recycled. Standardising on Recreus from day one means R&D investment compounds into eventual factory pellet production rather than being thrown away.

## The two architectures we're building toward

The generator outputs *the comfort core*. What goes on the surface is determined by use case:

**Architecture A — integral skin (showroom / exposed surface pieces):**
Print FilaFlex Foamy with temperature programming. Outer walls at 215°C (no foaming, denser ~82A skin) flowing into infill at 245°C (max foaming, ~60A core). Single material, single pass, gradient skin. Mimics integral-skin PU foam used in automotive. Slicer profile in `slicer-profiles.md`.

**Architecture C — production / fabric-covered:**
Print FilaFlex Foamy at 245°C throughout (full foaming). The geometry handles the comfort. Dacron wrap + standard upholstery fabric over the printed core, applied via Krošlák's existing sewing process. The print is the *engineered foam replacement*; the fabric is the visible/touch surface as in any normal sofa. This is the production target. The 3D-printed comfort engine slots into the existing upholstery process — the production floor learns nothing new about the outer envelope.

**For the generator, both architectures use the same geometry.** The difference is in the slicer (temperature, walls) and downstream process (coating vs fabric), not in the STL/3MF.

## Half-armrest specification

- **Footprint:** 100 × 90 mm rounded rectangle (corner radius 8 mm)
- **Height:** parameter — typical range 10–25 mm, default 15 mm
- **Top:** flat (forearm rests on it; no dome)
- **Bottom:** 1 mm solid base for adhesion + future mounting features
- **Lattice:** sheet gyroid TPMS, graded by both cell size and wall thickness along z
- **Gradient:** quadratic (z²) — keeps lower third firm, softens through upper two-thirds
- **Default cell size:** 4 mm at base → 9 mm at top
- **Default wall thickness:** 0.65 mm at base → 0.22 mm at top
- **Plate fit:** four parts fit comfortably on the 256 × 256 P2S build plate (matrix mode)

## Generator design rules

1. **Voxelise → marching cubes → decimate → export.** The proven pipeline; do not change without good reason.
2. **Always fix normals.** Marching cubes + decimation flips them. After every `simplify_quadric_decimation` call, check `mesh.volume < 0` and call `mesh.invert()` if true.
3. **3MF first, STL second.** 3MF is ~3× smaller and is Bambu Studio's native format. Always export both.
4. **Decimate aggressively.** Target 100–500k faces per part. Bambu Studio chokes on >1M face TPMS meshes.
5. **Print stats to console** every run: dimensions, solid volume (cm³), TPU mass at 1.21 g/cm³, face count, and voxel grid size. These numbers tell you whether the parameters make physical sense before you slice.
6. **Always write the seed parameters into the output filename** so there's no ambiguity about which file came from what settings: `armrest_h15_L4-9_t065-022_grad2.3mf`.

## Parameter reference (the design space)

These are the knobs that matter for furniture comfort. Ranges are practical ranges for the P2S + 0.6 mm nozzle + soft TPU. Outside these ranges the print fails or the part feels wrong.

| Parameter | Default | Practical range | What it does | When to change it |
|---|---|---|---|---|
| `width` | 100 mm | 80–150 mm | Long axis of footprint | Match the actual armrest length you're prototyping |
| `depth` | 90 mm | 60–110 mm | Short axis of footprint | Match the actual armrest width |
| `height` | 15 mm | 8–30 mm | Total z-height including base | Thicker = more comfort range. Below 10 mm the gradient has no room to express itself. |
| `corner_radius` | 8 mm | 3–15 mm | Footprint corner softening | Bigger = softer industrial silhouette; smaller = crisper edges |
| `base_thickness` | 1.0 mm | 0.6–2.0 mm | Solid bottom layer | Bigger = stronger mounting surface; smaller = saves material and print time |
| `voxel` | 0.5 mm | 0.3–0.8 mm | Voxelisation resolution | Smaller = smoother surface but exponentially slower + more RAM. 0.5 is the sweet spot. |
| `L_bottom` | 4.0 mm | 3.0–8.0 mm | Cell size at z=0 | Smaller = denser support, higher load capacity. Below 3 mm the 0.6 nozzle can't form clean walls. |
| `L_top` | 9.0 mm | 6.0–18.0 mm | Cell size at z=H | Bigger = sparser, more compliant, more breathable. Above 18 mm cells become visually obvious. |
| `t_bottom` | 0.65 mm | 0.45–0.85 mm | TPMS offset at z=0 | Bigger = thicker walls = firmer base. Below 0.45 the base feels weak under sit weight. |
| `t_top` | 0.22 mm | 0.15–0.35 mm | TPMS offset at z=H | Smaller = thinner walls = softer touch. Below 0.15 mm walls don't print reliably on 0.6 nozzle. |
| `gradient_power` | 2.0 | 0.5–4.0 | Curve of the firm→soft transition along z | 1.0 = linear; 2.0 = "firm base + comfort top" (default); 3.0 = "very firm base + mostly soft"; 0.5 = inverted (soft base, firm top — weird, almost never useful) |
| `target_faces` | 200_000 | 50k–800k | Mesh decimation target | Lower = faster slice but visible faceting. 200k is good for 100×90 parts. |

### How to tune for feel

- **Too firm overall** → drop both `t_bottom` and `t_top` by 0.1, OR raise `gradient_power` to 2.5
- **Too soft overall** → raise both `t_bottom` and `t_top` by 0.1, OR drop `gradient_power` to 1.5
- **Bottoms out under weight** → raise `t_bottom` (firmer base), keep `t_top` low (preserve surface compliance)
- **Surface feels rubbery, not foam-like** → switch to FilaFlex Foamy (filament change, not parameter change)
- **Cell pattern visible on the surface, looks "lattice-y"** → drop `L_top`, raise `L_bottom` (smaller cells throughout = smoother visual)

## Iteration workflow with Claude Code

The script is the bench, not the answer. Drive it like this:

```
"Generate the default 15mm half-armrest"
→ run generate.py with defaults, get armrest_h15_default.3mf

"Make me a 2×2 comparison plate: 12mm and 18mm height, two cell sizes (small 3-7mm, big 6-12mm)"
→ Claude Code adds matrix mode if not present, generates one 3MF with 4 parts on a plate

"Same as last one but with quadratic gradient instead of linear"
→ Claude Code re-runs with gradient_power=2.0

"The 18mm small-cell one was best. Make 5 variants of just that one with t_bottom from 0.45 to 0.85 in steps"
→ Claude Code generates a sweep plate for fine-tuning

"Now make a 200×90 full armrest with the same parameters"
→ Claude Code scales up
```

The script should evolve to support these moves with minimal nagging. Add CLI args, add helper functions, add a `presets.py` if useful — whatever makes the next iteration faster.

## Suggested first prints (in order)

1. **Single default 15 mm half-armrest in TPU 85A, Architecture C settings.** Validates the workflow end-to-end on the material we already own. ~3–4 hour print, ~50 g.

2. **2×2 plate with two heights (12, 18 mm) × two cell densities (small 3–7, big 6–12), all in TPU 85A.** First real comparison data. Press each, compare, write down which feels best.

3. **The winner from #2, reprinted in FilaFlex Foamy, Architecture C (245°C all).** First foaming print. Compare against the 85A version for the foam-character delta.

4. **Same winner, FilaFlex Foamy, Architecture A (215°C walls / 245°C infill).** First integral-skin print. Compare surface against #3.

5. **Wrap #3 in Dacron + Krošlák fabric.** Hand to Olena, Juraj, then sit on it. This is the production-readiness moment.

## Files in this folder

- `CLAUDE.md` — this file (project context)
- `generate.py` — the parametric generator (working baseline)
- `slicer-profiles.md` — print settings for TPU 85A, Foamy A, Foamy C
- `requirements.txt` — Python deps

## Constraints to honour

- **Don't propose pellet-printer geometry tricks the P2S can't print.** Multi-material, dissolvable supports, variable nozzle diameters — none available on this rig.
- **Don't suggest non-Recreus filaments without a reason.** We are intentionally standardising on Recreus across filament + pellet for ecosystem coherence.
- **Don't optimise the script into illegibility.** Samo iterates by reading the parameter block at the top. Keep that block clean and commented even if internals get clever.
- **Don't strip the console stats output.** Those numbers are how we know whether to hit "slice" or re-run with different parameters.
