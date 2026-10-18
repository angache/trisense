#!/usr/bin/env python3
"""Generate TriSense Spider S03 — tapered L-seat PLA basket for DIY 8\" (ID 185).

Matches assets/spider-diy8-s03-concept.png:
  - conical bowl (wide top → narrow bottom)
  - L flange on shell rim under mesh/hoop
  - segmented L tabs with flex gaps (built as tabs, not severed cuts)
  - no 3-arm spider; sensors on raised bowl platforms
  - pad tops so TriFlex+felt (~35 mm) / pos foam reach mesh plane

Usage:
  ../triflex-cone/.venv/bin/python cad/generate_spider_s03.py \
      models/experimental/trisense-spider-diy8-s03.stl
"""

from __future__ import annotations

import sys
from pathlib import Path

import manifold3d as mf
import numpy as np
import trimesh

# --- Envelope (concept) ---
L_OD_MM = 198.0
SKIRT_OD_MM = 183.5
BOTTOM_OD_MM = 150.0
WALL_T_MM = 3.5
FLANGE_T_MM = 4.0
BOWL_H_MM = 45.0

MESH_Z_MM = BOWL_H_MM + FLANGE_T_MM  # 49
FLANGE_Z0_MM = BOWL_H_MM

CENTER_STACK_MM = 35.0
POS_STACK_MM = 33.0
CENTER_PAD_TOP_Z = MESH_Z_MM - CENTER_STACK_MM  # 14
POS_PAD_TOP_Z = MESH_Z_MM - POS_STACK_MM  # 16
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

N_SEG = 12
GAP_DEG = 1.5  # narrow — less flex
L_DROP_MM = 22.5  # half wall height

N_WINDOWS = 6
WINDOW_R0 = 34.0
WINDOW_R1 = BOTTOM_OD_MM / 2 - WALL_T_MM - 10.0
WINDOW_HALF_W = 12.0

JACK_HOLE_OD_MM = 10.0
JACK_Z_MM = 20.0
JACK_ANGLE_DEG = 15.0  # center of an L leg (not in a çentik gap)

SEG = 72


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


def cyl(r: float, h: float, z0: float = 0.0) -> mf.Manifold:
    m = trimesh.creation.cylinder(radius=r, height=h, sections=SEG)
    m.apply_translation([0.0, 0.0, z0 + h / 2])
    return to_mf(m)


def box(sx: float, sy: float, sz: float, cx: float, cy: float, z0: float) -> mf.Manifold:
    m = trimesh.creation.box(extents=[sx, sy, sz])
    m.apply_translation([cx, cy, z0 + sz / 2])
    return to_mf(m)


def translate(solid: mf.Manifold, x: float, y: float, z: float = 0.0) -> mf.Manifold:
    raw = solid.to_mesh()
    tm = trimesh.Trimesh(
        np.asarray(raw.vert_properties)[:, :3],
        np.asarray(raw.tri_verts),
        process=False,
    )
    tm.apply_translation([x, y, z])
    return to_mf(tm)


def frustum_solid(r_bot: float, r_top: float, h: float, z0: float) -> mf.Manifold:
    theta = np.linspace(0, 2 * np.pi, SEG, endpoint=False)
    bot = np.column_stack(
        [r_bot * np.cos(theta), r_bot * np.sin(theta), np.full(SEG, z0)]
    )
    top = np.column_stack(
        [r_top * np.cos(theta), r_top * np.sin(theta), np.full(SEG, z0 + h)]
    )
    return to_mf(trimesh.convex.convex_hull(np.vstack([bot, top])))


def annular_sector(
    r_in: float, r_out: float, a0_deg: float, a1_deg: float, h: float, z0: float
) -> mf.Manifold:
    """Solid annular sector (L tab)."""
    n = max(8, int(SEG * abs(a1_deg - a0_deg) / 360.0))
    theta = np.radians(np.linspace(a0_deg, a1_deg, n))
    # prism via extrusion of 2D polygon
    ring = np.vstack(
        [
            np.column_stack([r_out * np.cos(theta), r_out * np.sin(theta)]),
            np.column_stack([r_in * np.cos(theta[::-1]), r_in * np.sin(theta[::-1])]),
        ]
    )
    poly = trimesh.path.polygons.paths_to_polygons([ring])  # may fail
    # manual extrude
    verts_bot = np.column_stack([ring, np.full(len(ring), z0)])
    verts_top = np.column_stack([ring, np.full(len(ring), z0 + h)])
    verts = np.vstack([verts_bot, verts_top])
    npts = len(ring)
    faces = []
    # sides
    for i in range(npts):
        j = (i + 1) % npts
        faces.append([i, j, npts + j])
        faces.append([i, npts + j, npts + i])
    # caps — fan from centroid projection (use earclip via trimesh)
    tm = trimesh.Trimesh(vertices=verts, faces=faces, process=False)
    # better: use extrusion
    try:
        path = trimesh.load_path(ring)
        ext = path.extrude(h)
        if isinstance(ext, list):
            ext = ext[0]
        ext.apply_translation([0, 0, z0])
        return to_mf(ext)
    except Exception:
        pass
    # fallback convex hull of the sector points (works for <180°)
    if abs(a1_deg - a0_deg) < 179:
        return to_mf(trimesh.convex.convex_hull(verts))
    return to_mf(tm)


def annular_sector_hull(
    r_in: float, r_out: float, a0_deg: float, a1_deg: float, h: float, z0: float
) -> mf.Manifold:
    """Annular sector as convex hull of inner/outer arcs at bot+top (span < 180°)."""
    n = max(6, int(SEG * abs(a1_deg - a0_deg) / 360.0) + 2)
    theta = np.radians(np.linspace(a0_deg, a1_deg, n))
    pts = []
    for z in (z0, z0 + h):
        for r in (r_in, r_out):
            pts.append(
                np.column_stack([r * np.cos(theta), r * np.sin(theta), np.full(n, z)])
            )
    return to_mf(trimesh.convex.convex_hull(np.vstack(pts)))


def tapered_wall_sector(
    a0_deg: float,
    a1_deg: float,
    z0: float,
    z1: float,
    r0_out: float,
    r1_out: float,
    wall_t: float,
) -> mf.Manifold:
    """One L vertical leg: tapered wall sector (hollow thickness via hull of 4 arcs)."""
    n = max(6, int(SEG * abs(a1_deg - a0_deg) / 360.0) + 2)
    theta = np.radians(np.linspace(a0_deg, a1_deg, n))
    pts = []
    for z, r_out in ((z0, r0_out), (z1, r1_out)):
        r_in = max(r_out - wall_t, 1.0)
        pts.append(np.column_stack([r_out * np.cos(theta), r_out * np.sin(theta), np.full(n, z)]))
        pts.append(np.column_stack([r_in * np.cos(theta), r_in * np.sin(theta), np.full(n, z)]))
    return to_mf(trimesh.convex.convex_hull(np.vstack(pts)))


def build() -> trimesh.Trimesh:
    r_bot = BOTTOM_OD_MM / 2
    r_top = SKIRT_OD_MM / 2
    floor_r = r_bot - WALL_T_MM + 0.8

    # Solid ring at bottom; above that wall is ONLY L segments (true deep çentik)
    h_ring = max(BOWL_H_MM - L_DROP_MM, 6.0)
    r_ring = r_bot + (r_top - r_bot) * (h_ring / BOWL_H_MM)
    outer = frustum_solid(r_bot, r_ring, h_ring, 0.0)
    inner = frustum_solid(
        max(r_bot - WALL_T_MM, 1.0),
        max(r_ring - WALL_T_MM, 1.0),
        h_ring + 2.0,
        -1.0,
    )
    solid = outer - inner

    # Each L: tapered vertical leg from ring → flange + horizontal seat
    seg_span = 360.0 / N_SEG
    tab_span = seg_span - GAP_DEG
    for i in range(N_SEG):
        a0 = i * seg_span + GAP_DEG / 2
        a1 = a0 + tab_span
        leg = tapered_wall_sector(
            a0, a1, h_ring, FLANGE_Z0_MM, r_ring, r_top, WALL_T_MM
        )
        # vertical continues through flange thickness at skirt OD
        leg_cap = annular_sector_hull(
            r_top - WALL_T_MM, r_top, a0, a1, FLANGE_T_MM, FLANGE_Z0_MM
        )
        seat = annular_sector_hull(
            r_top - WALL_T_MM, L_OD_MM / 2, a0, a1, FLANGE_T_MM, FLANGE_Z0_MM
        )
        solid = solid + leg + leg_cap + seat

    # Floor + pads
    solid = solid + cyl(floor_r, FLOOR_T_MM, 0.0)
    solid = solid + cyl(CENTER_PAD_OD_MM / 2, CENTER_PAD_TOP_Z, 0.0)
    for k in range(3):
        phase = 2 * np.pi * k / 3
        px = R_POS_MM * np.cos(phase)
        py = R_POS_MM * np.sin(phase)
        solid = solid + translate(cyl(POS_PAD_OD_MM / 2, POS_PAD_TOP_Z, 0.0), px, py)

    # Ribs between windows
    for i in range(N_WINDOWS):
        ang = np.degrees(2 * np.pi * i / N_WINDOWS)
        inner, outer_r = 18.0, floor_r - 2.0
        length = outer_r - inner
        rib = box(length, 8.0, 6.0, inner + length / 2, 0.0, 0.0)
        solid = solid + rib.rotate([0.0, 0.0, ang])

    cuts: list[mf.Manifold] = []

    # Floor windows between ribs; avoid pos-pad rays
    for i in range(N_WINDOWS):
        ang = 2 * np.pi * i / N_WINDOWS + np.pi / N_WINDOWS
        deg = np.degrees(ang) % 360
        if min(abs(((deg - p + 180) % 360) - 180) for p in (0.0, 120.0, 240.0)) < 25:
            ang += np.radians(25)
        r_c = 0.5 * (WINDOW_R0 + WINDOW_R1)
        length = WINDOW_R1 - WINDOW_R0
        win = box(length, WINDOW_HALF_W * 2, FLOOR_T_MM + 6.0, r_c, 0.0, -1.0)
        cuts.append(win.rotate([0.0, 0.0, np.degrees(ang)]))

    # Pockets
    cuts.append(cyl(CENTER_HOLE_OD_MM / 2, CENTER_PAD_TOP_Z + 4.0, -1.0))
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
    for k in range(3):
        phase = 2 * np.pi * k / 3
        px = R_POS_MM * np.cos(phase)
        py = R_POS_MM * np.sin(phase)
        rec = cyl(
            POS_PIEZO_OD_MM / 2,
            POS_PIEZO_DEPTH_MM + 0.15,
            POS_PAD_TOP_Z - POS_PIEZO_DEPTH_MM,
        )
        cuts.append(translate(rec, px, py))

    for k in range(3):
        phase = 2 * np.pi * k / 3
        inner = CENTER_HOLE_OD_MM / 2 + 2.0
        outer = R_POS_MM
        length = outer - inner
        g = box(length, 3.5, 1.6, inner + length / 2, 0.0, -0.1)
        cuts.append(g.rotate([0.0, 0.0, np.degrees(phase)]))

    # Jack between pads
    t = np.clip(JACK_Z_MM / BOWL_H_MM, 0.05, 0.95)
    r_jack = r_bot + (r_top - r_bot) * t
    jh = cyl(JACK_HOLE_OD_MM / 2, WALL_T_MM + 10.0, -(WALL_T_MM + 10.0) / 2)
    jh = jh.rotate([0.0, 90.0, 0.0])
    jh = translate(jh, r_jack - WALL_T_MM / 2, 0.0, JACK_Z_MM)
    jh = jh.rotate([0.0, 0.0, JACK_ANGLE_DEG])
    cuts.append(jh)

    for c in cuts:
        solid = solid - c

    raw = solid.to_mesh()
    mesh = trimesh.Trimesh(
        vertices=np.asarray(raw.vert_properties)[:, :3],
        faces=np.asarray(raw.tri_verts),
        process=True,
    )
    parts = mesh.split(only_watertight=False)
    if len(parts) > 1:
        # drop only dust; keep everything with meaningful volume
        keep = [p for p in parts if (p.is_volume and p.volume > 50) or len(p.faces) > 80]
        if not keep:
            keep = sorted(parts, key=lambda m: len(m.faces), reverse=True)[:1]
        mesh = trimesh.util.concatenate(keep)
        print(f"note: merged {len(keep)}/{len(parts)} components")
    return mesh


def main(argv: list[str]) -> int:
    out = Path(
        argv[1] if len(argv) > 1 else "models/experimental/trisense-spider-diy8-s03.stl"
    )
    mesh = build()
    size = mesh.bounds[1] - mesh.bounds[0]
    print("bbox size:", np.round(size, 3))
    print("bounds:", np.round(mesh.bounds, 3).tolist())
    print("watertight:", mesh.is_watertight)
    print("volume:", round(float(mesh.volume), 1) if mesh.is_volume else "n/a")
    print("faces:", len(mesh.faces))
    print("components:", len(mesh.split(only_watertight=False)))
    print(f"mesh_z (L top): {MESH_Z_MM}")
    print(f"center_pad_top: {CENTER_PAD_TOP_Z} (+{CENTER_STACK_MM} → mesh)")
    print(f"pos_pad_top: {POS_PAD_TOP_Z} (+{POS_STACK_MM} → mesh)")
    out.parent.mkdir(parents=True, exist_ok=True)
    mesh.export(out)
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
