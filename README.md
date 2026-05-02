# Quickstart

## First run (one-time setup)

```bash
cd kroslak-tpu
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/Mac
pip install -r requirements.txt
python generate.py              # default 100×90×15 mm armrest
python generate.py --matrix     # 2×2 comparison plate
```

Output goes to `./out/` as paired `.3mf` and `.stl` files. The 3MF is what you load in Bambu Studio.

## Vibe-coding patterns with Claude Code

Open this folder in Claude Code (`claude .` from the directory). Claude Code reads `CLAUDE.md` automatically — it knows the project, the hardware, the design space, and the constraints.

Then drive it with prompts like:

### Single-part generation
- *"Generate a 12mm half-armrest with smaller cells, like 3mm at the base"*
- *"Make me a 20mm version with the most aggressive softness gradient you'd recommend"*
- *"Generate the same thing but for the full 200×90 armrest size"*

### Comparison plates
- *"Make a 2×2 plate comparing gradient_power values: 1.5, 2.0, 2.5, 3.0 — keep everything else default at 15mm height"*
- *"Generate a horizontal sweep: 5 parts in a row, each one with t_top from 0.15 to 0.35 in 0.05 steps. Same dimensions otherwise."*
- *"Build me a height test: 4 parts, heights 8/12/18/25mm, all same lattice settings"*

### Following up after a print
- *"The thick_small variant from the matrix print felt best. Make me a refined version: same parameters but try 0.55 wall thickness at the base instead of 0.65, and a 2.3 gradient instead of 2.0"*
- *"Print felt too firm overall. Drop both wall thicknesses by 0.1 and re-export"*
- *"Bottoms out under hand pressure. Keep top settings, raise t_bottom to 0.85"*

### Geometry experiments
- *"Add a parameter for an asymmetric height: thicker at the front (where the wrist rests) tapering to thinner at the back"*
- *"Add 5mm raised side lips along the long edges so the forearm doesn't slip off"*
- *"Add M5 boss holes in the bottom solid base for bolting onto a metal arm — pattern: four corners inset 15mm"*

### Workflow improvements
- *"Add a `--preview` flag that opens trimesh.Scene to visually verify before exporting"*
- *"Add a `presets.py` with named configurations: 'soft_armrest', 'firm_lumbar', 'thin_seat_topper'"*
- *"Add a post-processor that takes a sliced G-code and inserts M104 commands per feature for Architecture A integral skin"*
- *"Generate a markdown table summary of all parameters across all the variants in the matrix and save it next to the 3MF"*

## What the script does NOT do (yet)

These are intentional gaps. Ask Claude Code to add them as you need them — having them as named TODOs keeps the baseline script readable.

- **Mounting features** (boss holes, keyholes, t-slots) — add when you have a real metal arm CAD to mate to
- **Asymmetric thickness** — useful for ergonomic taper but not validated in tests yet
- **Side lips / containment edges** — only needed if specific use case demands
- **Variable density per region (not just per z-slab)** — useful for body-mapped seats but premature for armrest stage
- **Pellet-machine G-code preview** — relevant when scaling to in-house pellet extrusion, not yet
- **Multiple footprint shapes** (hexagon, organic blob from outline) — current rounded rectangle covers all near-term needs

## Iteration discipline

The fastest way to wreck this workflow is to change ten things at once between prints. Change ONE parameter per iteration when you can. Note what changed. Press the printed part. Write down what you felt. Then change the next thing.

The whole point of having a parametric generator is that the design space is searchable. Random variations defeat that.
