"""
Half-armrest comfort sample generator
=====================================
Generates graded sheet-gyroid TPMS lattice cushions for the Krošlák TPU
comfort R&D project. Outputs Bambu-Studio-ready 3MF (and STL fallback)
sized for the Bambu Lab P2S (256×256 build plate).

Usage
-----
    # Default 100×90×15 mm half-armrest with sensible parameters
    python generate.py

    # Override key parameters from the CLI
    python generate.py --height 20 --L-bottom 3 --L-top 7 --gradient 2.5

    # Matrix mode: 2×2 plate of variants (heights × cell sizes)
    python generate.py --matrix

    # Custom output name
    python generate.py --height 18 --name forearm_v3

Design principle
----------------
Sheet gyroid TPMS, graded by both cell size and wall thickness along z.
Bottom = small cells + thick walls = firm load-bearing base.
Top    = large cells + thin walls  = soft compliant comfort surface.
Quadratic z² gradient mimics how good HR foam cushions are constructed:
firm support layer, comfort top zone, smooth transition between.

Output normals are auto-fixed (marching cubes + decimation invert them).
"""

from __future__ import annotations
import argparse
from dataclasses import dataclass, field
from pathlib import Path
import sys

# Force utf-8 stdout/stderr so unicode chars (×, ³, →) survive on Windows cp1252
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure") and (_stream.encoding or "").lower() != "utf-8":
        _stream.reconfigure(encoding="utf-8", errors="replace")

import numpy as np
import trimesh
from skimage import measure


# =============================================================================
# DEFAULTS — tweak here, or override via CLI
# =============================================================================

@dataclass
class ArmrestParams:
    # Geometry (mm)
    width:          float = 100.0  # long axis of footprint
    depth:          float = 90.0   # short axis of footprint
    height:         float = 15.0   # total z height (includes solid base)
    corner_radius:  float = 8.0    # rounded-rectangle corner softening
    base_thickness: float = 1.0    # solid bottom layer (adhesion + mounting)

    # Lattice — see CLAUDE.md "Parameter reference" for tuning guidance
    L_bottom:        float = 4.0   # cell size at z=0 (smaller = denser)
    L_top:           float = 9.0   # cell size at z=H (bigger = sparser)
    t_bottom:        float = 0.65  # TPMS wall offset at z=0 (bigger = firmer)
    t_top:           float = 0.22  # TPMS wall offset at z=H (smaller = softer)
    gradient_power:  float = 2.0   # 1=linear, 2=firm-base+soft-top, 3=very-firm-base

    # Mesh quality
    voxel:           float = 0.5     # voxelisation resolution (mm)
    target_faces:    int   = 200_000 # decimation target

    # Surface test — solid top cap covering a sub-region of the footprint.
    # Set skin_thickness > 0 to enable. skin_x_min/max are in part-frame mm
    # (footprint is centred on origin, so x ranges from -width/2 to +width/2).
    # When None, defaults to the full x extent (full top skin).
    skin_thickness:  float = 0.0
    skin_x_min:      float | None = None
    skin_x_max:      float | None = None

    # I/O
    name:            str  = "armrest"
    out_dir:         Path = field(default_factory=lambda: Path("./out"))

    # Material density estimate (TPU baseline; Foamy is lower when foamed)
    density_g_cm3:   float = 1.21


# =============================================================================
# GEOMETRY HELPERS
# =============================================================================

def rounded_rect_mask(x_grid: np.ndarray,
                      y_grid: np.ndarray,
                      width: float,
                      depth: float,
                      radius: float) -> np.ndarray:
    """Boolean mask: True where (x,y) is inside a rounded rectangle of size
    width × depth, corner radius `radius`, centred on origin.

    Uses the standard SDF: distance from inner inset rectangle minus radius.
    """
    half_w = width  / 2.0 - radius
    half_h = depth  / 2.0 - radius
    qx = np.maximum(np.abs(x_grid) - half_w, 0.0)
    qy = np.maximum(np.abs(y_grid) - half_h, 0.0)
    sdf = np.sqrt(qx * qx + qy * qy) - radius
    return sdf <= 0.0


def build_part(p: ArmrestParams,
               x_offset: float = 0.0,
               y_offset: float = 0.0) -> trimesh.Trimesh:
    """Generate a single graded-gyroid armrest mesh.

    Returns a trimesh.Trimesh translated so that its centre-of-footprint
    is at (x_offset, y_offset, 0) and its base sits at z=0.

    Boolean voxel grid → marching cubes at level=0.5. The bool grid is the
    cleanest topology for sheet-gyroid lattices — sharper than an analytic SDF
    (whose |f| cusp at f=0 produces ambiguous MC cells) and far cleaner than
    aggressively decimated MC output (which destroys manifold-ness on lattice
    meshes). When face count after MC is reasonable, we skip decimation
    entirely; quadric decimation on lattice meshes inevitably produces
    thousands of non-manifold edges that slow the slicer.
    """
    # ---- Voxel grid ----------------------------------------------------------
    nx = int(np.ceil(p.width  / p.voxel)) + 2
    ny = int(np.ceil(p.depth  / p.voxel)) + 2
    nz = int(np.ceil(p.height / p.voxel)) + 2

    xs = np.linspace(-p.width  / 2 - p.voxel,
                      p.width  / 2 + p.voxel, nx, dtype=np.float32)
    ys = np.linspace(-p.depth  / 2 - p.voxel,
                      p.depth  / 2 + p.voxel, ny, dtype=np.float32)
    zs = np.linspace(0.0, p.height + p.voxel, nz, dtype=np.float32)

    Xg, Yg = np.meshgrid(xs, ys, indexing="ij")
    inside_footprint = rounded_rect_mask(Xg, Yg, p.width, p.depth, p.corner_radius)

    # Skin region (surface test): defaults to full x extent if bounds unset
    skin_x_min = p.skin_x_min if p.skin_x_min is not None else -p.width / 2.0
    skin_x_max = p.skin_x_max if p.skin_x_max is not None else +p.width / 2.0
    in_skin_xy = (Xg >= skin_x_min) & (Xg <= skin_x_max)

    solid = np.zeros((nx, ny, nz), dtype=bool)

    # ---- Per-z-slab evaluation (memory-friendly) -----------------------------
    for iz, zv in enumerate(zs):
        if not inside_footprint.any():
            continue

        # Solid base layer
        if zv < p.base_thickness:
            solid[:, :, iz] = inside_footprint
            continue

        # Anything above total height: empty
        if zv > p.height:
            continue

        # Gradient: 0 at base, 1 at top, raised to gradient_power
        z_norm = (zv - p.base_thickness) / max(1e-6, p.height - p.base_thickness)
        z_norm = np.clip(z_norm, 0.0, 1.0)
        grad   = z_norm ** p.gradient_power

        # Interpolated cell size and wall thickness for this slab
        L = p.L_bottom + (p.L_top - p.L_bottom) * grad
        t = p.t_bottom + (p.t_top - p.t_bottom) * grad
        k = 2.0 * np.pi / L

        # Sheet gyroid: |sin(kx)cos(ky) + sin(ky)cos(kz) + sin(kz)cos(kx)| < t
        sin_kx = np.sin(k * xs)[:, None].astype(np.float32)
        cos_kx = np.cos(k * xs)[:, None].astype(np.float32)
        sin_ky = np.sin(k * ys)[None, :].astype(np.float32)
        cos_ky = np.cos(k * ys)[None, :].astype(np.float32)
        sin_kz = float(np.sin(k * zv))
        cos_kz = float(np.cos(k * zv))

        gyroid = (sin_kx * cos_ky
                  + sin_ky * cos_kz
                  + sin_kz * cos_kx)

        # Surface test: in skin region within the top skin_thickness slab,
        # boost the gyroid threshold so cells fill in completely (max |f| ≈
        # 1.5 < 2.0). Keeps everything as gyroid topology — no boolean OR
        # with a separate box.
        if p.skin_thickness > 0 and zv > p.height - p.skin_thickness:
            t_grid = np.where(in_skin_xy, 2.0, t).astype(np.float32)
            solid[:, :, iz] = inside_footprint & (np.abs(gyroid) < t_grid)
        else:
            solid[:, :, iz] = inside_footprint & (np.abs(gyroid) < t)

    # ---- Marching cubes ------------------------------------------------------
    # Pad with one zero-layer so the surface closes cleanly. allow_degenerate=False
    # drops sliver triangles skimage would otherwise emit.
    padded = np.pad(solid.astype(np.float32), 1, constant_values=0.0)
    verts, faces, _, _ = measure.marching_cubes(padded, level=0.5,
                                                spacing=(p.voxel,) * 3,
                                                allow_degenerate=False)

    # Recentre: subtract the padding offset and the original grid offset
    verts[:, 0] -= (p.width  / 2 + 2 * p.voxel)
    verts[:, 1] -= (p.depth  / 2 + 2 * p.voxel)
    verts[:, 2] -= p.voxel

    mesh = trimesh.Trimesh(vertices=verts, faces=faces, process=True)

    # ---- Decimate (when needed) ---------------------------------------------
    # fast_simplification at low aggression (≤2) refuses to make collapses
    # that would break manifold-ness, so it hits a "lossless floor" well
    # short of the requested target_count. For our lattice meshes this floor
    # cuts face count ~40-60% with a few hundred non-manifold edges — vastly
    # better than aggression≥5 which destroys topology (50k+ non-manifolds).
    # Skipped entirely if target_faces is huge (caller opted out).
    if len(mesh.faces) > p.target_faces:
        import fast_simplification
        v_d, f_d = fast_simplification.simplify(
            mesh.vertices.astype(np.float64),
            mesh.faces.astype(np.uint32),
            target_count=p.target_faces, agg=2.0,
        )
        mesh = trimesh.Trimesh(vertices=v_d, faces=f_d, process=True)
        mesh.merge_vertices()
        mesh.update_faces(mesh.unique_faces())
        mesh.update_faces(mesh.nondegenerate_faces())
        mesh.remove_unreferenced_vertices()

    # ---- Fix inverted normals (marching cubes + decimation flips them) -------
    if mesh.volume < 0:
        mesh.invert()

    # ---- Translate to plate position ----------------------------------------
    mesh.apply_translation([x_offset, y_offset, 0.0])

    return mesh


# =============================================================================
# OUTPUT
# =============================================================================

def export_and_report(meshes: list[trimesh.Trimesh],
                      params_for_filename: ArmrestParams,
                      label: str = "") -> Path:
    """Concatenate, export 3MF + STL, print stats. Returns 3MF path."""
    if len(meshes) == 1:
        scene_mesh = meshes[0]
    else:
        scene_mesh = trimesh.util.concatenate(meshes)

    p = params_for_filename
    p.out_dir.mkdir(parents=True, exist_ok=True)

    suffix = label or (
        f"h{int(p.height)}"
        f"_L{p.L_bottom:g}-{p.L_top:g}"
        f"_t{p.t_bottom:g}-{p.t_top:g}"
        f"_grad{p.gradient_power:g}"
    )
    # Build paths via string concat — Path.with_suffix() incorrectly strips
    # numeric "extensions" like ".22" from parameter values in the suffix.
    base = p.out_dir / f"{p.name}_{suffix}"
    path_3mf = Path(str(base) + ".3mf")
    path_stl = Path(str(base) + ".stl")
    scene_mesh.export(path_3mf)
    scene_mesh.export(path_stl)

    bounds = scene_mesh.bounds
    dims   = bounds[1] - bounds[0]
    vol_cm3 = scene_mesh.volume / 1000.0
    mass_g  = vol_cm3 * p.density_g_cm3

    # Count non-manifold edges — the slicer can usually handle them but a high
    # count (10k+) makes Bambu Studio's Windows mesh-repair service hang.
    from collections import Counter
    edge_counts = Counter(map(tuple, scene_mesh.edges_sorted))
    nonmanifold = sum(1 for c in edge_counts.values() if c > 2)

    print()
    print(f"=== {base.name} ===")
    print(f"  Bounds:        {dims[0]:.1f} × {dims[1]:.1f} × {dims[2]:.1f} mm")
    print(f"  Solid volume:  {vol_cm3:.1f} cm³")
    print(f"  Estimated mass:{mass_g:6.0f} g  (TPU @ {p.density_g_cm3} g/cm³)")
    print(f"  Faces:         {len(scene_mesh.faces):,}")
    print(f"  Non-manifold:  {nonmanifold} edges  (skip Bambu Repair if > 1000)")
    print(f"  3MF file:      {path_3mf}")
    print(f"  STL fallback:  {path_stl}")
    print()
    return path_3mf


# =============================================================================
# CLI
# =============================================================================

def parse_cli() -> tuple[ArmrestParams, argparse.Namespace]:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--width",          type=float, default=100.0)
    ap.add_argument("--depth",          type=float, default=90.0)
    ap.add_argument("--height",         type=float, default=15.0)
    ap.add_argument("--corner-radius",  type=float, default=8.0)
    ap.add_argument("--base-thickness", type=float, default=1.0)
    ap.add_argument("--L-bottom",       type=float, default=4.0)
    ap.add_argument("--L-top",          type=float, default=9.0)
    ap.add_argument("--t-bottom",       type=float, default=0.65)
    ap.add_argument("--t-top",          type=float, default=0.22)
    ap.add_argument("--gradient",       type=float, default=2.0,
                    help="Gradient curve power (1=linear, 2=firm-base+soft-top)")
    ap.add_argument("--voxel",          type=float, default=0.5)
    ap.add_argument("--target-faces",   type=int,   default=200_000)
    ap.add_argument("--name",           type=str,   default="armrest")
    ap.add_argument("--out-dir",        type=Path,  default=Path("./out"))
    ap.add_argument("--density",        type=float, default=1.21,
                    help="Material density g/cm³ (TPU 85A solid=1.21; "
                         "Foamy fully foamed @245°C ≈ 0.85)")
    ap.add_argument("--matrix", action="store_true",
                    help="Generate the default 2×2 comparison plate (10/20 mm)")
    ap.add_argument("--thin-matrix", action="store_true",
                    help="Generate a 2×2 plate at 3 mm and 5 mm with a "
                         "solid-skin surface test on the right third of each part")

    args = ap.parse_args()
    params = ArmrestParams(
        width=args.width, depth=args.depth, height=args.height,
        corner_radius=args.corner_radius, base_thickness=args.base_thickness,
        L_bottom=args.L_bottom, L_top=args.L_top,
        t_bottom=args.t_bottom, t_top=args.t_top,
        gradient_power=args.gradient,
        voxel=args.voxel, target_faces=args.target_faces,
        name=args.name, out_dir=args.out_dir,
        density_g_cm3=args.density,
    )
    return params, args


def matrix_plate(base: ArmrestParams) -> None:
    """Generate a 2×2 comparison plate.
    Layout (looking down at the plate):
        front-left  : thin   + small cells
        front-right : thin   + big cells
        back-left   : thick  + small cells
        back-right  : thick  + big cells
    """
    spacing = 12.0  # mm gap between parts
    pitch_x = base.width  + spacing
    pitch_y = base.depth  + spacing

    variants = [
        # (label,                height, L_bot, L_top, x_pos,        y_pos)
        ("thin_small",  10.0, 3.5, 7.0, -pitch_x / 2,  -pitch_y / 2),
        ("thin_big",    10.0, 6.0, 12.0, +pitch_x / 2, -pitch_y / 2),
        ("thick_small", 20.0, 3.5, 7.0, -pitch_x / 2,  +pitch_y / 2),
        ("thick_big",   20.0, 6.0, 12.0, +pitch_x / 2, +pitch_y / 2),
    ]

    meshes = []
    for label, h, L_bot, L_top, x, y in variants:
        p = ArmrestParams(
            width=base.width, depth=base.depth, height=h,
            corner_radius=base.corner_radius, base_thickness=base.base_thickness,
            L_bottom=L_bot, L_top=L_top,
            t_bottom=base.t_bottom, t_top=base.t_top,
            gradient_power=base.gradient_power,
            voxel=base.voxel, target_faces=base.target_faces // 2,
            density_g_cm3=base.density_g_cm3,
        )
        print(f"  building variant: {label}  h={h}mm  L={L_bot}-{L_top}mm")
        meshes.append(build_part(p, x_offset=x, y_offset=y))

    export_and_report(meshes, base, label="matrix_2x2")


def thin_skin_matrix_plate(base: ArmrestParams) -> None:
    """2×2 plate at 3 mm and 5 mm heights × dense and sparse densities.

    Each part has a 0.6 mm solid top skin on its right third (surface
    treatment test); the left two-thirds keep the open gyroid top.
    Same gyroid below the skin in both regions, so the only variable
    in the skin/no-skin split is the closed surface itself.

    Layout (looking down at the plate):
        front-left  : 3 mm dense
        front-right : 3 mm sparse
        back-left   : 5 mm dense
        back-right  : 5 mm sparse
    """
    spacing = 12.0
    pitch_x = base.width + spacing
    pitch_y = base.depth + spacing

    # Skin region: right third along x. Boundary at +width/6.
    skin_x_min = base.width / 6.0
    skin_x_max = base.width / 2.0
    skin_thickness = 0.6  # ~1 line width on a 0.6 nozzle

    # Wall thickness in mm ≈ t · L / π. Values below keep all walls ≥ 0.6 mm.
    # Cells are slightly larger than CLAUDE.md's defaults to make the lattice
    # visually less cramped at this scale (100×90 mm part shouldn't show 30
    # cells across).
    variants = [
        # label,         h,   L_bot, L_top, t_bot, t_top, x_pos,        y_pos
        ("h3_dense",   3.0,   5.0,   8.0,   0.50,  0.35, -pitch_x / 2, -pitch_y / 2),
        ("h3_sparse",  3.0,   7.0,  11.0,   0.35,  0.22, +pitch_x / 2, -pitch_y / 2),
        ("h5_dense",   5.0,   5.0,   8.0,   0.50,  0.35, -pitch_x / 2, +pitch_y / 2),
        ("h5_sparse",  5.0,   7.0,  11.0,   0.35,  0.22, +pitch_x / 2, +pitch_y / 2),
    ]

    meshes = []
    for label, h, L_bot, L_top, t_bot, t_top, x, y in variants:
        p = ArmrestParams(
            width=base.width, depth=base.depth, height=h,
            corner_radius=base.corner_radius, base_thickness=base.base_thickness,
            L_bottom=L_bot, L_top=L_top,
            t_bottom=t_bot, t_top=t_top,
            gradient_power=1.5,
            # voxel=0.6 lands the post-decimation total under 1M faces —
            # comfortably below Bambu Studio's complexity warning. Walls
            # (0.78-0.89 mm) capture as 1.3-1.5 voxels, on the marginal side
            # but acceptable for these large-cell lattices. Trade is more
            # non-manifold edges (~5k vs 200 at voxel=0.45) but slicer
            # processes fewer faces per layer.
            voxel=0.6,
            # Lossless floor in fast_simplification: cuts faces ~40-60% while
            # preserving manifold-ness; refuses to collapse further regardless
            # of target_faces.
            target_faces=50_000,
            density_g_cm3=base.density_g_cm3,
            skin_thickness=skin_thickness,
            skin_x_min=skin_x_min,
            skin_x_max=skin_x_max,
        )
        print(f"  building variant: {label}  h={h}mm  L={L_bot}-{L_top}mm  "
              f"t={t_bot}-{t_top}  skin=right_third")
        meshes.append(build_part(p, x_offset=x, y_offset=y))

    export_and_report(meshes, base, label="thin_2x2_h3-h5_dense-sparse_skin")


def main() -> int:
    params, args = parse_cli()

    if args.thin_matrix:
        print("\nGenerating thin 2×2 plate (3 + 5 mm) with right-third skin surface test...")
        thin_skin_matrix_plate(params)
    elif args.matrix:
        print("\nGenerating 2×2 comparison plate...")
        matrix_plate(params)
    else:
        print(f"\nGenerating single half-armrest "
              f"({params.width:g} × {params.depth:g} × {params.height:g} mm)...")
        mesh = build_part(params)
        export_and_report([mesh], params)

    print("Done.\n"
          "Next step: drop the .3mf into Bambu Studio, right-click → Repair model,\n"
          "apply the slicer profile from slicer-profiles.md, and slice.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
