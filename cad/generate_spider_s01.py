#!/usr/bin/env python3
"""Generate TriSense Spider S01 — PLA basket for DIY 8\" pad (ID 185 mm).

Usage:
  /path/to/triflex-cone/.venv/bin/python cad/generate_spider_s01.py \
      models/experimental/trisense-spider-diy8-s01.stl
"""

from __future__ import annotations

import sys
from pathlib import Path

import manifold3d as mf
import numpy as np
import trimesh

# Envelope (locked from user measure + plan)
INNER_DIAMETER_MM = 185.0
R_POS_MM = 60.0
R_FOOT_MM = 88.0
R_MAX_MM = 90.0

PLATE_T_MM = 3.5
HUB_OD_MM = 44.0
TRIFLEX_POCKET_OD_MM = 39.0
TRIFLEX_POCKET_DEPTH_MM = 1.2
CENTER_PIEZO_OD_MM = 29.0
CENTER_PIEZO_DEPTH_MM = 0.6
CENTER_HOLE_OD_MM = 12.0

POS_PIEZO_OD_MM = 22.0
POS_PIEZO_DEPTH_MM = 0.6
POS_PAD_OD_MM = 28.0

ARM_WIDTH_MM = 28.0
FOOT_OD_MM = 14.0
FOOT_H_MM = 4.0

CABLE_W_MM = 3.5
CABLE_D_MM = 1.5

# Downward pan-jack pocket on arm 0 (toward +X)
JACK_HOLE_OD_MM = 10.0
JACK_FLANGE_OD_MM = 16.0
JACK_R_MM = 38.0  # from center along +X
JACK_POCKET_DEPTH_MM = PLATE_T_MM  # through

SEG = 64


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


def arm_solid(phase: float) -> mf.Manifold:
    """Rectangular arm from near hub to position pad, in XY, thickness PLATE_T."""
    # Arm along +X then rotate about Z by phase
    inner = HUB_OD_MM / 2 - 1.0
    outer = R_POS_MM + POS_PAD_OD_MM / 2 - 1.0
    length = outer - inner
    cx = inner + length / 2
    solid = box(length, ARM_WIDTH_MM, PLATE_T_MM, cx, 0.0, 0.0)
    # rotate
    angle = phase
    c, s = np.cos(angle), np.sin(angle)
    # manifold rotate expects degrees about axis
    return solid.rotate([0.0, 0.0, np.degrees(angle)])


def build() -> trimesh.Trimesh:
    parts: list[mf.Manifold] = []

    # Hub disk
    parts.append(cyl(HUB_OD_MM / 2, PLATE_T_MM, 0.0))

    # Three arms + position pads + feet
    for k in range(3):
        phase = 2 * np.pi * k / 3
        parts.append(arm_solid(phase))
        # position pad
        px = R_POS_MM * np.cos(phase)
        py = R_POS_MM * np.sin(phase)
        pad = cyl(POS_PAD_OD_MM / 2, PLATE_T_MM, 0.0)
        # translate pad
        raw = pad.to_mesh()
        tm = trimesh.Trimesh(
            np.asarray(raw.vert_properties)[:, :3],
            np.asarray(raw.tri_verts),
            process=False,
        )
        tm.apply_translation([px, py, 0])
        parts.append(to_mf(tm))
        # foot under arm tip (slightly outward)
        fx = R_FOOT_MM * np.cos(phase)
        fy = R_FOOT_MM * np.sin(phase)
        foot = cyl(FOOT_OD_MM / 2, FOOT_H_MM, -FOOT_H_MM)
        rawf = foot.to_mesh()
        tf = trimesh.Trimesh(
            np.asarray(rawf.vert_properties)[:, :3],
            np.asarray(rawf.tri_verts),
            process=False,
        )
        tf.apply_translation([fx, fy, 0])
        parts.append(to_mf(tf))

    # Thin outer ring segments connecting feet (stiffen) — optional arcs as boxes
    for k in range(3):
        a0 = 2 * np.pi * k / 3 + 0.35
        a1 = 2 * np.pi * ((k + 1) % 3) / 3 - 0.35
        # short chord box at R_FOOT
        mid = 0.5 * (a0 + a1)
        if a1 < a0:
            mid = (a0 + a1 + 2 * np.pi) / 2
        chord = R_FOOT_MM * abs(a1 - a0)
        if a1 < a0:
            chord = R_FOOT_MM * (a1 + 2 * np.pi - a0)
        cx = R_FOOT_MM * np.cos(mid)
        cy = R_FOOT_MM * np.sin(mid)
        seg = box(max(chord, 8), 8.0, PLATE_T_MM, 0, 0, 0)
        seg = seg.rotate([0, 0, np.degrees(mid)])
        raw = seg.to_mesh()
        ts = trimesh.Trimesh(
            np.asarray(raw.vert_properties)[:, :3] + np.array([cx, cy, 0]),
            np.asarray(raw.tri_verts),
            process=False,
        )
        # simpler: just skip ring segments if messy — use feet only
        _ = ts

    solid = parts[0]
    for p in parts[1:]:
        solid = solid + p

    # --- subtracts ---
    cuts: list[mf.Manifold] = []

    # Center hole through
    cuts.append(cyl(CENTER_HOLE_OD_MM / 2, PLATE_T_MM + 2, -1))

    # TriFlex pocket from top
    pocket = cyl(TRIFLEX_POCKET_OD_MM / 2, TRIFLEX_POCKET_DEPTH_MM + 0.2, PLATE_T_MM - TRIFLEX_POCKET_DEPTH_MM)
    cuts.append(pocket)

    # Center piezo shallow recess (bottom of pocket area — from top of plate)
    # Recess on TOP face inside TriFlex pocket for adhesive piezo seat clarity:
    # actually piezo sits under TriFlex on plate; recess on TOP of plate center annulus
    piezo_c = cyl(CENTER_PIEZO_OD_MM / 2, CENTER_PIEZO_DEPTH_MM + 0.1, PLATE_T_MM - CENTER_PIEZO_DEPTH_MM)
    cuts.append(piezo_c)

    # Position piezo recesses
    for k in range(3):
        phase = 2 * np.pi * k / 3
        px = R_POS_MM * np.cos(phase)
        py = R_POS_MM * np.sin(phase)
        rec = cyl(POS_PIEZO_OD_MM / 2, POS_PIEZO_DEPTH_MM + 0.1, PLATE_T_MM - POS_PIEZO_DEPTH_MM)
        raw = rec.to_mesh()
        tr = trimesh.Trimesh(
            np.asarray(raw.vert_properties)[:, :3],
            np.asarray(raw.tri_verts),
            process=False,
        )
        tr.apply_translation([px, py, 0])
        cuts.append(to_mf(tr))

    # Cable grooves underside (z=0 face): from each pos to hub, and hub to jack
    for k in range(3):
        phase = 2 * np.pi * k / 3
        # groove along arm, underside
        inner = CENTER_HOLE_OD_MM / 2 + 2
        outer = R_POS_MM
        length = outer - inner
        g = box(length, CABLE_W_MM, CABLE_D_MM + 0.2, inner + length / 2, 0, -0.1)
        g = g.rotate([0, 0, np.degrees(phase)])
        cuts.append(g)

    # Jack through-hole at +X
    jh = cyl(JACK_HOLE_OD_MM / 2, PLATE_T_MM + FOOT_H_MM + 2, -FOOT_H_MM - 1)
    raw = jh.to_mesh()
    tj = trimesh.Trimesh(
        np.asarray(raw.vert_properties)[:, :3],
        np.asarray(raw.tri_verts),
        process=False,
    )
    tj.apply_translation([JACK_R_MM, 0, 0])
    cuts.append(to_mf(tj))
    # flange clearance counterbore from bottom
    jf = cyl(JACK_FLANGE_OD_MM / 2, 1.2, -1.2)
    raw = jf.to_mesh()
    tf = trimesh.Trimesh(
        np.asarray(raw.vert_properties)[:, :3],
        np.asarray(raw.tri_verts),
        process=False,
    )
    tf.apply_translation([JACK_R_MM, 0, 0])
    cuts.append(to_mf(tf))

    for c in cuts:
        solid = solid - c

    # Safety: clip to R_MAX cylinder
    envelope = cyl(R_MAX_MM, PLATE_T_MM + FOOT_H_MM + 2, -FOOT_H_MM - 1)
    solid = solid ^ envelope

    raw = solid.to_mesh()
    mesh = trimesh.Trimesh(
        vertices=np.asarray(raw.vert_properties)[:, :3],
        faces=np.asarray(raw.tri_verts),
        process=True,
    )
    return mesh


def main(argv: list[str]) -> int:
    out = Path(argv[1] if len(argv) > 1 else "models/experimental/trisense-spider-diy8-s01.stl")
    mesh = build()
    size = mesh.bounds[1] - mesh.bounds[0]
    print("bbox size:", np.round(size, 3))
    print("bounds:", np.round(mesh.bounds, 3).tolist())
    print("watertight:", mesh.is_watertight)
    print("volume:", round(float(mesh.volume), 1) if mesh.is_watertight else "n/a")
    print("faces:", len(mesh.faces))
    xy = max(size[0], size[1])
    if xy > INNER_DIAMETER_MM - 2:
        print("WARNING: XY exceeds safe ID clearance", INNER_DIAMETER_MM)
    out.parent.mkdir(parents=True, exist_ok=True)
    mesh.export(out)
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
