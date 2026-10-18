#!/usr/bin/env python3
"""Generate TriSense Spider S02 — shell-seat PLA basket for DIY 8\" (ID 185 mm).

S01 was a flat deck with tip feet — it had no outer wall to seat in the shell.
S02 adds the functional architecture used by commercial digital-pad baskets:
  - continuous outer rim that seats against the shell ID
  - bowl depth (rim height) so the deck hangs at a controlled stack height
  - radial jack cutout through the rim wall
  - flex slots so the rim can spring slightly for a snug fit
  - three arms + hub for center TriFlex + position piezos

Not a copy of any manufacturer's part — same job, DIY scale, open sectors.

Usage:
  ../triflex-cone/.venv/bin/python cad/generate_spider_s02.py \
      models/experimental/trisense-spider-diy8-s02.stl
"""

from __future__ import annotations

import sys
from pathlib import Path

import manifold3d as mf
import numpy as np
import trimesh

# --- Shell envelope (user-measured DIY 8") ---
SHELL_ID_MM = 185.0
RIM_OD_MM = 183.0  # ~1 mm diametral clearance; flex slots take up snug fit
RIM_WALL_MM = 3.2
RIM_H_MM = 32.0  # bowl depth / seating wall height

# Sensor deck sits near the top of the bowl so couplers reach the mesh
DECK_TOP_Z_MM = 28.0  # absolute Z of deck top face (basket bottom = 0)
PLATE_T_MM = 3.5
DECK_Z0_MM = DECK_TOP_Z_MM - PLATE_T_MM  # deck bottom Z

R_POS_MM = 60.0
HUB_OD_MM = 44.0
TRIFLEX_POCKET_OD_MM = 39.0
TRIFLEX_POCKET_DEPTH_MM = 1.2
CENTER_PIEZO_OD_MM = 29.0
CENTER_PIEZO_DEPTH_MM = 0.6
CENTER_HOLE_OD_MM = 12.0

POS_PIEZO_OD_MM = 22.0
POS_PIEZO_DEPTH_MM = 0.6
POS_PAD_OD_MM = 28.0
ARM_WIDTH_MM = 26.0

# Underside cable grooves on deck
CABLE_W_MM = 3.5
CABLE_D_MM = 1.5

# Radial stereo jack through rim wall (+X)
JACK_HOLE_OD_MM = 10.0
JACK_FLANGE_OD_MM = 16.0
JACK_CUTOUT_W_MM = 18.0  # rectangular wall relief around jack
JACK_CUTOUT_H_MM = 14.0
JACK_Z_MM = 14.0  # hole center height from basket bottom

# Rim flex / hardware clearance slots (not at jack)
N_FLEX_SLOTS = 5
FLEX_SLOT_W_MM = 6.0
FLEX_SLOT_H_MM = 18.0
FLEX_SLOT_Z0_MM = 0.0

# Light bottom flange under rim (helps sit on pad floor)
FLANGE_W_MM = 4.0
FLANGE_T_MM = 2.0

SEG = 96


def to_mf(mesh: trimesh.Trimesh) -> mf.Manifold:
    mesh = mesh.copy()
    mesh.merge_vertices()
    if mesh.volume < 0:
        mesh.invert()
    return mf.Manifold(
        mf.Mesh(
            vert_properties=mesh.vertices.astype(np.float32),
            tri_verts=mesh.faces.astype(np.uint32),
        )
    )


def cyl(r: float, h: float, z0: float = 0.0) -> mf.Manifold:
    m = trimesh.creation.cylinder(radius=r, height=h, sections=SEG)
    m.apply_translation([0, 0, z0 + h / 2])
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


def rim_tube() -> mf.Manifold:
    outer = cyl(RIM_OD_MM / 2, RIM_H_MM, 0.0)
    inner_r = RIM_OD_MM / 2 - RIM_WALL_MM
    inner = cyl(inner_r, RIM_H_MM + 2, -1.0)
    return outer - inner


def bottom_flange() -> mf.Manifold:
    """Annular lip under the rim — rests on pad floor / foam."""
    outer = cyl(RIM_OD_MM / 2, FLANGE_T_MM, 0.0)
    # leave center open; flange only under wall + a bit inward
    inner_r = RIM_OD_MM / 2 - RIM_WALL_MM - FLANGE_W_MM
    inner = cyl(inner_r, FLANGE_T_MM + 2, -1.0)
    return outer - inner


def arm_solid(phase: float) -> mf.Manifold:
    """Arm from hub to inner rim face, at deck height."""
    inner = HUB_OD_MM / 2 - 1.0
    outer = RIM_OD_MM / 2 - RIM_WALL_MM + 1.0  # bite into rim for union
    length = outer - inner
    cx = inner + length / 2
    solid = box(length, ARM_WIDTH_MM, PLATE_T_MM, cx, 0.0, DECK_Z0_MM)
    return solid.rotate([0.0, 0.0, np.degrees(phase)])


def build() -> trimesh.Trimesh:
    parts: list[mf.Manifold] = [rim_tube(), bottom_flange()]

    # Hub disk at deck
    parts.append(cyl(HUB_OD_MM / 2, PLATE_T_MM, DECK_Z0_MM))

    for k in range(3):
        phase = 2 * np.pi * k / 3
        parts.append(arm_solid(phase))
        px = R_POS_MM * np.cos(phase)
        py = R_POS_MM * np.sin(phase)
        pad = cyl(POS_PAD_OD_MM / 2, PLATE_T_MM, DECK_Z0_MM)
        parts.append(translate(pad, px, py, 0.0))

    solid = parts[0]
    for p in parts[1:]:
        solid = solid + p

    cuts: list[mf.Manifold] = []

    # Center through-hole
    cuts.append(cyl(CENTER_HOLE_OD_MM / 2, PLATE_T_MM + 4, DECK_Z0_MM - 2))

    # TriFlex + center piezo pockets from deck top
    cuts.append(
        cyl(
            TRIFLEX_POCKET_OD_MM / 2,
            TRIFLEX_POCKET_DEPTH_MM + 0.2,
            DECK_TOP_Z_MM - TRIFLEX_POCKET_DEPTH_MM,
        )
    )
    cuts.append(
        cyl(
            CENTER_PIEZO_OD_MM / 2,
            CENTER_PIEZO_DEPTH_MM + 0.1,
            DECK_TOP_Z_MM - CENTER_PIEZO_DEPTH_MM,
        )
    )

    for k in range(3):
        phase = 2 * np.pi * k / 3
        px = R_POS_MM * np.cos(phase)
        py = R_POS_MM * np.sin(phase)
        rec = cyl(
            POS_PIEZO_OD_MM / 2,
            POS_PIEZO_DEPTH_MM + 0.1,
            DECK_TOP_Z_MM - POS_PIEZO_DEPTH_MM,
        )
        cuts.append(translate(rec, px, py, 0.0))

    # Cable grooves on deck underside
    for k in range(3):
        phase = 2 * np.pi * k / 3
        inner = CENTER_HOLE_OD_MM / 2 + 2
        outer = R_POS_MM
        length = outer - inner
        g = box(
            length,
            CABLE_W_MM,
            CABLE_D_MM + 0.2,
            inner + length / 2,
            0,
            DECK_Z0_MM - 0.1,
        )
        cuts.append(g.rotate([0, 0, np.degrees(phase)]))

    # Radial jack: hole + flange counterbore from outside + wall cutout
    jack_len = RIM_WALL_MM + FLANGE_W_MM + 6.0
    jh = cyl(JACK_HOLE_OD_MM / 2, jack_len, -jack_len / 2)
    # cylinder default is along Z; rotate to +X and place at rim
    jh = jh.rotate([0, 90, 0])
    jh = translate(jh, RIM_OD_MM / 2 - RIM_WALL_MM / 2, 0.0, JACK_Z_MM)
    cuts.append(jh)

    jf = cyl(JACK_FLANGE_OD_MM / 2, 2.0, -1.0)
    jf = jf.rotate([0, 90, 0])
    jf = translate(jf, RIM_OD_MM / 2 - 0.5, 0.0, JACK_Z_MM)
    cuts.append(jf)

    # Rectangular wall relief around jack (easier nut access)
    cutout = box(
        RIM_WALL_MM + 4,
        JACK_CUTOUT_W_MM,
        JACK_CUTOUT_H_MM,
        RIM_OD_MM / 2 - RIM_WALL_MM / 2,
        0.0,
        JACK_Z_MM - JACK_CUTOUT_H_MM / 2,
    )
    cuts.append(cutout)

    # Flex slots around rim (skip jack sector near +X)
    for i in range(N_FLEX_SLOTS):
        ang = 2 * np.pi * (i + 0.5) / N_FLEX_SLOTS  # offset from +X
        # skip if too close to jack
        if abs((ang + np.pi) % (2 * np.pi) - np.pi) < 0.35:
            continue
        slot = box(
            RIM_WALL_MM + 4,
            FLEX_SLOT_W_MM,
            FLEX_SLOT_H_MM,
            RIM_OD_MM / 2 - RIM_WALL_MM / 2,
            0.0,
            FLEX_SLOT_Z0_MM,
        )
        slot = slot.rotate([0, 0, np.degrees(ang)])
        cuts.append(slot)

    for c in cuts:
        solid = solid - c

    raw = solid.to_mesh()
    mesh = trimesh.Trimesh(
        vertices=np.asarray(raw.vert_properties)[:, :3],
        faces=np.asarray(raw.tri_verts),
        process=True,
    )
    return mesh


def main(argv: list[str]) -> int:
    out = Path(
        argv[1] if len(argv) > 1 else "models/experimental/trisense-spider-diy8-s02.stl"
    )
    mesh = build()
    size = mesh.bounds[1] - mesh.bounds[0]
    print("bbox size:", np.round(size, 3))
    print("bounds:", np.round(mesh.bounds, 3).tolist())
    print("watertight:", mesh.is_watertight)
    print("volume:", round(float(mesh.volume), 1) if mesh.is_watertight else "n/a")
    print("faces:", len(mesh.faces))
    print("components:", len(mesh.split(only_watertight=False)))
    xy = max(size[0], size[1])
    if xy > SHELL_ID_MM - 0.5:
        print("WARNING: XY may bind in shell ID", SHELL_ID_MM)
    out.parent.mkdir(parents=True, exist_ok=True)
    mesh.export(out)
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
