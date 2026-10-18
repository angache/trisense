#!/usr/bin/env python3
"""TriSense Spider S05 — hub + flower-petal modular bowl (DIY 8\").

Architecture (print-friendly):
  - Center HUB: TriFlex / center piezo seat + join rim
  - 3 PETALS around the hub (like flower petals), each with one pos pad + L wall
  - Join hub↔petal and petal↔petal: overlapping tabs + M3 (glue/snap optional)

Seams sit in çentik gaps so L legs stay whole.
S03 monolith is unchanged; this is the printable kit.

Usage:
  ../triflex-cone/.venv/bin/python cad/generate_spider_s05.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import manifold3d as mf
import numpy as np
import trimesh

# --- Same envelope as S03 ---
L_OD_MM = 198.0
SKIRT_OD_MM = 183.5
BOTTOM_OD_MM = 150.0
WALL_T_MM = 3.5
FLANGE_T_MM = 4.0
BOWL_H_MM = 45.0
MESH_Z_MM = BOWL_H_MM + FLANGE_T_MM
FLANGE_Z0_MM = BOWL_H_MM
CENTER_STACK_MM = 35.0
POS_STACK_MM = 33.0
CENTER_PAD_TOP_Z = MESH_Z_MM - CENTER_STACK_MM
POS_PAD_TOP_Z = MESH_Z_MM - POS_STACK_MM
FLOOR_T_MM = 3.5

R_POS_MM = 55.0
CENTER_PAD_OD_MM = 44.0
TRIFLEX_POCKET_OD_MM = 39.0
TRIFLEX_POCKET_DEPTH_MM = 1.2
CENTER_PIEZO_OD_MM = 29.0
CENTER_PIEZO_DEPTH_MM = 0.6
CENTER_HOLE_OD_MM = 12.0
POS_PAD_OD_MM = 28.0
POS_PIEZO_OD_MM = 22.0
POS_PIEZO_DEPTH_MM = 0.6

N_L_TABS = 12
GAP_DEG = 1.5
L_DROP_MM = 22.5

N_PETALS = 3
# Hub = center seat + surround for joins (pos pads stay on petals)
HUB_OD_MM = 72.0
HUB_R = HUB_OD_MM / 2
JOIN_OVERLAP_MM = 8.0  # petal underlaps hub rim
TAB_W_DEG = 14.0  # hub tab angular width
M3 = 3.2
JACK_HOLE_OD_MM = 10.0
JACK_Z_MM = 20.0
# petal 0 midline = 0°; jack on that petal's wall
JACK_ANGLE_DEG = 0.0

SEG = 72
ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "models" / "experimental"


def to_mf(mesh: trimesh.Trimesh) -> mf.Manifold:
    mesh = mesh.copy()
    mesh.merge_vertices(1e-4)
    mesh.update_faces(mesh.unique_faces())
    mesh.remove_unreferenced_vertices()
    mesh.fix_normals()
    try:
        if mesh.volume < 0:
            mesh.invert()
    except Exception:
        pass
    return mf.Manifold(
        mf.Mesh(
            vert_properties=mesh.vertices.astype(np.float32),
            tri_verts=mesh.faces.astype(np.uint32),
        )
    )


def mf_mesh(solid: mf.Manifold) -> trimesh.Trimesh:
    raw = solid.to_mesh()
    return trimesh.Trimesh(
        np.asarray(raw.vert_properties)[:, :3],
        np.asarray(raw.tri_verts),
        process=True,
    )


def cyl(r: float, h: float, z0: float = 0.0) -> mf.Manifold:
    m = trimesh.creation.cylinder(radius=r, height=h, sections=SEG)
    m.apply_translation([0, 0, z0 + h / 2])
    return to_mf(m)


def box(sx, sy, sz, cx, cy, z0) -> mf.Manifold:
    m = trimesh.creation.box(extents=[sx, sy, sz])
    m.apply_translation([cx, cy, z0 + sz / 2])
    return to_mf(m)


def translate(solid: mf.Manifold, x, y, z=0.0) -> mf.Manifold:
    tm = mf_mesh(solid)
    tm.apply_translation([x, y, z])
    return to_mf(tm)


def frustum_solid(r_bot, r_top, h, z0) -> mf.Manifold:
    th = np.linspace(0, 2 * np.pi, SEG, endpoint=False)
    bot = np.column_stack([r_bot * np.cos(th), r_bot * np.sin(th), np.full(SEG, z0)])
    top = np.column_stack([r_top * np.cos(th), r_top * np.sin(th), np.full(SEG, z0 + h)])
    return to_mf(trimesh.convex.convex_hull(np.vstack([bot, top])))


def annular_sector_hull(r_in, r_out, a0, a1, h, z0) -> mf.Manifold:
    n = max(6, int(SEG * abs(a1 - a0) / 360) + 2)
    th = np.radians(np.linspace(a0, a1, n))
    pts = []
    for z in (z0, z0 + h):
        for r in (r_in, r_out):
            pts.append(np.column_stack([r * np.cos(th), r * np.sin(th), np.full(n, z)]))
    return to_mf(trimesh.convex.convex_hull(np.vstack(pts)))


def tapered_wall_sector(a0, a1, z0, z1, r0_out, r1_out, wall_t) -> mf.Manifold:
    n = max(6, int(SEG * abs(a1 - a0) / 360) + 2)
    th = np.radians(np.linspace(a0, a1, n))
    pts = []
    for z, r_out in ((z0, r0_out), (z1, r1_out)):
        r_in = max(r_out - wall_t, 1.0)
        pts.append(np.column_stack([r_out * np.cos(th), r_out * np.sin(th), np.full(n, z)]))
        pts.append(np.column_stack([r_in * np.cos(th), r_in * np.sin(th), np.full(n, z)]))
    return to_mf(trimesh.convex.convex_hull(np.vstack(pts)))


def wedge(a0, a1, r_max, z0, h) -> mf.Manifold:
    n = max(8, int(SEG * abs(a1 - a0) / 360) + 2)
    th = np.radians(np.linspace(a0, a1, n))
    arc = np.column_stack([r_max * np.cos(th), r_max * np.sin(th)])
    poly = np.vstack([[0.0, 0.0], arc])
    pts = [np.column_stack([poly, np.full(len(poly), z)]) for z in (z0, z0 + h)]
    return to_mf(trimesh.convex.convex_hull(np.vstack(pts)))


def build_full_bowl(with_jack: bool) -> mf.Manifold:
    r_bot, r_top = BOTTOM_OD_MM / 2, SKIRT_OD_MM / 2
    floor_r = r_bot - WALL_T_MM + 0.8
    h_ring = max(BOWL_H_MM - L_DROP_MM, 6.0)
    r_ring = r_bot + (r_top - r_bot) * (h_ring / BOWL_H_MM)

    outer = frustum_solid(r_bot, r_ring, h_ring, 0.0)
    inner = frustum_solid(
        max(r_bot - WALL_T_MM, 1.0), max(r_ring - WALL_T_MM, 1.0), h_ring + 2.0, -1.0
    )
    solid = outer - inner

    span = 360.0 / N_L_TABS
    tab = span - GAP_DEG
    for i in range(N_L_TABS):
        a0 = i * span + GAP_DEG / 2
        a1 = a0 + tab
        leg = tapered_wall_sector(a0, a1, h_ring, FLANGE_Z0_MM, r_ring, r_top, WALL_T_MM)
        cap = annular_sector_hull(r_top - WALL_T_MM, r_top, a0, a1, FLANGE_T_MM, FLANGE_Z0_MM)
        seat = annular_sector_hull(
            r_top - WALL_T_MM, L_OD_MM / 2, a0, a1, FLANGE_T_MM, FLANGE_Z0_MM
        )
        solid = solid + leg + cap + seat

    solid = solid + cyl(floor_r, FLOOR_T_MM, 0.0)
    solid = solid + cyl(CENTER_PAD_OD_MM / 2, CENTER_PAD_TOP_Z, 0.0)

    for k in range(N_PETALS):
        ph = 2 * np.pi * k / N_PETALS
        pad = cyl(POS_PAD_OD_MM / 2, POS_PAD_TOP_Z, 0.0)
        solid = solid + translate(pad, R_POS_MM * np.cos(ph), R_POS_MM * np.sin(ph))

    cuts: list[mf.Manifold] = []
    # (no floor windows on petals — solid deck)

    cuts.append(cyl(CENTER_HOLE_OD_MM / 2, CENTER_PAD_TOP_Z + 4, -1))
    cuts.append(
        cyl(
            TRIFLEX_POCKET_OD_MM / 2,
            TRIFLEX_POCKET_DEPTH_MM + 0.25,
            CENTER_PAD_TOP_Z - TRIFLEX_POCKET_DEPTH_MM,
        )
    )
    cuts.append(
        cyl(
            CENTER_PIEZO_OD_MM / 2,
            CENTER_PIEZO_DEPTH_MM + 0.15,
            CENTER_PAD_TOP_Z - CENTER_PIEZO_DEPTH_MM,
        )
    )
    for k in range(N_PETALS):
        ph = 2 * np.pi * k / N_PETALS
        px, py = R_POS_MM * np.cos(ph), R_POS_MM * np.sin(ph)
        rec = cyl(
            POS_PIEZO_OD_MM / 2,
            POS_PIEZO_DEPTH_MM + 0.15,
            POS_PAD_TOP_Z - POS_PIEZO_DEPTH_MM,
        )
        cuts.append(translate(rec, px, py))
        inner = CENTER_HOLE_OD_MM / 2 + 2
        g = box(R_POS_MM - inner, 3.5, 1.6, inner + (R_POS_MM - inner) / 2, 0, -0.1)
        cuts.append(g.rotate([0, 0, np.degrees(ph)]))

    if with_jack:
        t = np.clip(JACK_Z_MM / BOWL_H_MM, 0.05, 0.95)
        r_jack = r_bot + (r_top - r_bot) * t
        jh = cyl(JACK_HOLE_OD_MM / 2, WALL_T_MM + 10, -(WALL_T_MM + 10) / 2)
        jh = jh.rotate([0, 90, 0])
        jh = translate(jh, r_jack - WALL_T_MM / 2, 0, JACK_Z_MM)
        cuts.append(jh.rotate([0, 0, JACK_ANGLE_DEG]))

    for c in cuts:
        solid = solid - c
    return solid


def add_hub_petal_joins(hub: mf.Manifold, petals: list[mf.Manifold]) -> tuple[mf.Manifold, list[mf.Manifold]]:
    """Joins that do NOT stack floors on top of each other (no wall clash).

    Hub↔petal: hub tab nests in an open radial pocket in the petal floor + M3.
    Petal↔petal: facing pads on each side of the seam (butt), horizontal M3 —
    nothing crosses the seam into the neighbor's volume.
    """
    tab_r = HUB_R + JOIN_OVERLAP_MM / 2
    tab_len = JOIN_OVERLAP_MM + 2.0
    tab_h = FLOOR_T_MM  # flush with floor — sits in pocket
    span = 360.0 / N_PETALS
    clearance = 0.35  # gap between butt faces / pocket

    for k in range(N_PETALS):
        mid = k * span
        for off in (-22.0, 22.0):
            ang = mid + off
            # Hub tab
            tab = box(tab_len, 10.0, tab_h, tab_r, 0.0, 0.0).rotate([0, 0, ang])
            hub = hub + tab
            hole = translate(cyl(M3 / 2, tab_h + 8, -3), tab_r, 0, 0).rotate([0, 0, ang])
            hub = hub - hole
            # Open pocket in petal: radial slot from hub edge outward (no wall left in way)
            pocket = box(
                tab_len + 2.0,
                11.0,
                FLOOR_T_MM + 2.0,
                tab_r,
                0.0,
                -0.5,
            ).rotate([0, 0, ang])
            petals[k] = petals[k] - pocket
            petals[k] = petals[k] - hole

    # Petal↔petal: butt flanges — each stays on its own side of the seam
    pad_thick = 4.0
    pad_h = 10.0
    pad_z = 0.0
    r0 = HUB_R + 6.0
    r1 = BOTTOM_OD_MM / 2 - WALL_T_MM - 4.0
    r_c = 0.5 * (r0 + r1)
    radial = r1 - r0

    for k in range(N_PETALS):
        mid = k * span
        # a1 = CW seam, a0 = CCW seam
        for seam_off, y_inside in ((+span / 2, -pad_thick / 2 - clearance / 2),
                                   (-span / 2, +pad_thick / 2 + clearance / 2)):
            ang = mid + seam_off
            # flange entirely inside this petal (y_inside toward petal interior)
            pad = box(radial, pad_thick, pad_h, r_c, y_inside, pad_z).rotate([0, 0, ang])
            petals[k] = petals[k] + pad
            # horizontal M3 through pad (along local Y = into the seam)
            for r in (r_c - 8.0, r_c + 8.0):
                if r < r0 + 3 or r > r1 - 3:
                    continue
                h = cyl(M3 / 2, pad_thick + 8.0, -(pad_thick + 8.0) / 2)
                h = h.rotate([90, 0, 0])
                h = translate(h, r, y_inside, pad_h / 2).rotate([0, 0, ang])
                petals[k] = petals[k] - h

    # Keep join hardware inside skirt OD
    escaped = cyl(L_OD_MM / 2 + 10, pad_h + 6, -1) - cyl(SKIRT_OD_MM / 2 + 0.2, pad_h + 8, -2)
    hub = hub - escaped
    petals = [p - escaped for p in petals]
    return hub, petals


def cleanup(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    parts = mesh.split(only_watertight=False)
    if len(parts) <= 1:
        return mesh
    keep = [p for p in parts if (p.is_volume and p.volume > 80) or len(p.faces) > 100]
    if not keep:
        keep = [max(parts, key=lambda m: len(m.faces))]
    return trimesh.util.concatenate(keep)


def export(mesh: trimesh.Trimesh, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mesh = cleanup(mesh)
    mesh.export(path)
    s = mesh.bounds[1] - mesh.bounds[0]
    print(
        f"  {path.name}: {s[0]:.1f}×{s[1]:.1f}×{s[2]:.1f} mm  "
        f"wt={mesh.is_watertight}  faces={len(mesh.faces)}"
    )


def main() -> int:
    print("S05 hub + 3 petals (flower)")
    print(f"  hub OD={HUB_OD_MM}  petals={N_PETALS}  L_OD={L_OD_MM}")

    full = build_full_bowl(with_jack=True)

    # Hub core (slightly oversized cut so petals clear)
    hub_core = cyl(HUB_R + 0.15, MESH_Z_MM + 4, -1)
    hub = full ^ hub_core

    # Petals: bowl minus hub hole, then wedge. Seams at ±60° from midline (çentik).
    span = 360.0 / N_PETALS
    petals: list[mf.Manifold] = []
    bowl_shell = full - cyl(HUB_R - JOIN_OVERLAP_MM, MESH_Z_MM + 4, -1)
    for k in range(N_PETALS):
        mid = k * span
        a0, a1 = mid - span / 2, mid + span / 2
        w = wedge(a0 - 0.2, a1 + 0.2, L_OD_MM / 2 + 6, -2, MESH_Z_MM + 6)
        petals.append(bowl_shell ^ w)

    hub, petals = add_hub_petal_joins(hub, petals)

    export(mf_mesh(hub), OUT_DIR / "trisense-bowl-diy8-s05-hub.stl")
    letters = "abc"
    for i, p in enumerate(petals):
        export(mf_mesh(p), OUT_DIR / f"trisense-bowl-diy8-s05-petal-{letters[i]}.stl")

    note = OUT_DIR / "trisense-bowl-diy8-s05-README.txt"
    note.write_text(
        "TriSense bowl S05 — hub + 3 flower petals (diy8)\n\n"
        "Print: hub + petal-a (jack) + petal-b + petal-c\n\n"
        "Assembly:\n"
        "  1. Lay hub flat (TriFlex pocket up).\n"
        "  2. Slide each petal under the hub rim tabs (çiçek yaprakları).\n"
        "  3. M3 through hub tabs into petals (6×).\n"
        "  4. Mate petal sides: peg into pocket, M3 on floor laps, optional glue.\n"
        "  5. Petal-a faces the shell jack hole.\n\n"
        "S03 monolith remains the form reference.\n"
    )
    print("wrote", note.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
