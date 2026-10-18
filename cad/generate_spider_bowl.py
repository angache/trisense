#!/usr/bin/env python3
"""TriSense modular tapered L-seat bowl (S04) — parametric by shell size.

Standard form from S03 concept:
  conical bowl, segmented L flange under mesh, sensors on floor pads, no 3-arm spider.

Printed as N identical-ish sectors (default 3) with tongue/groove + M3 join holes.
Sector 0 includes the radial jack hole.

Usage:
  ../triflex-cone/.venv/bin/python cad/generate_spider_bowl.py diy8
  ../triflex-cone/.venv/bin/python cad/generate_spider_bowl.py tom14 --sectors 6
  ../triflex-cone/.venv/bin/python cad/generate_spider_bowl.py diy8 --monolith  # one piece (like S03)

Outputs under models/experimental/:
  trisense-bowl-{name}-s04-a.stl ... (sectors)
  trisense-bowl-{name}-s04.stl      (--monolith)
"""

from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import manifold3d as mf
import numpy as np
import trimesh

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

ROOT = Path(__file__).resolve().parents[1]
SIZES_PATH = Path(__file__).resolve().parent / "sizes.toml"
SEG = 72

CENTER_PAD_OD_MM = 44.0
TRIFLEX_POCKET_OD_MM = 39.0
TRIFLEX_POCKET_DEPTH_MM = 1.2
CENTER_PIEZO_OD_MM = 29.0
CENTER_PIEZO_DEPTH_MM = 0.6
CENTER_HOLE_OD_MM = 12.0
POS_PAD_OD_MM = 28.0
POS_PIEZO_OD_MM = 22.0
POS_PIEZO_DEPTH_MM = 0.6
FLOOR_T_MM = 3.5
JACK_HOLE_OD_MM = 10.0
JACK_Z_FRAC = 0.44  # of bowl_h

# Internal seam join (inside cavity only)
JOIN_IN_MM = 18.0  # flange depth into cavity
JOIN_THICK_MM = 5.0  # each face plate
JOIN_Z0_MM = 2.0
PIN_SIZE_MM = (10.0, 2.4, 12.0)
PIN_CLEAR_MM = 0.25


@dataclass
class BowlSpec:
    name: str
    inch: float
    shell_id_mm: float
    shell_od_mm: float
    l_od_mm: float
    skirt_od_mm: float
    bottom_od_mm: float
    r_pos_mm: float
    wall_t_mm: float
    flange_t_mm: float
    bowl_h_mm: float
    center_stack_mm: float
    pos_stack_mm: float
    n_l_tabs: int
    gap_deg: float
    l_drop_mm: float
    sectors: int
    bed_max_mm: float
    join_screw_od_mm: float
    join_boss_mm: float

    @property
    def mesh_z(self) -> float:
        return self.bowl_h_mm + self.flange_t_mm

    @property
    def center_pad_top_z(self) -> float:
        return self.mesh_z - self.center_stack_mm

    @property
    def pos_pad_top_z(self) -> float:
        return self.mesh_z - self.pos_stack_mm

    @property
    def flange_z0(self) -> float:
        return self.bowl_h_mm


def load_sizes() -> tuple[dict, list[dict]]:
    data = tomllib.loads(SIZES_PATH.read_text())
    return data["defaults"], data["size"]


def resolve_spec(name: str, sectors_override: int | None = None) -> BowlSpec:
    defaults, sizes = load_sizes()
    ratios = tomllib.loads(SIZES_PATH.read_text())["ratios"]
    row = next((s for s in sizes if s["name"] == name), None)
    if row is None:
        known = ", ".join(s["name"] for s in sizes)
        raise SystemExit(f"unknown size {name!r}. known: {known}")

    sid = float(row["shell_id_mm"])
    sod = float(row["shell_od_mm"])
    l_od = float(row.get("l_od_mm", sid + ratios["l_overhang_mm"]))
    skirt = float(row.get("skirt_od_mm", sid - ratios["skirt_clearance_mm"]))
    bottom = float(row.get("bottom_od_mm", sid * ratios["bottom_over_id"]))
    r_pos = float(row.get("r_pos_mm", sid * ratios["r_pos_over_id"]))

    # scale L tab count with circumference (~ every 50 mm)
    n_tabs = int(row.get("n_l_tabs", max(12, round(math.pi * l_od / 50.0))))
    if n_tabs % 3:
        n_tabs += 3 - (n_tabs % 3)

    sectors = int(sectors_override or defaults["sectors"])
    bed = float(defaults["bed_max_mm"])
    # auto-bump sector count so chord fits bed (keep multiple of 3 for 120° piezo symmetry)
    while True:
        chord = l_od * math.sin(math.pi / sectors)
        if chord <= bed or sectors >= 12:
            break
        sectors += 3

    return BowlSpec(
        name=row["name"],
        inch=float(row["inch"]),
        shell_id_mm=sid,
        shell_od_mm=sod,
        l_od_mm=l_od,
        skirt_od_mm=skirt,
        bottom_od_mm=bottom,
        r_pos_mm=r_pos,
        wall_t_mm=float(defaults["wall_t_mm"]),
        flange_t_mm=float(defaults["flange_t_mm"]),
        bowl_h_mm=float(defaults["bowl_h_mm"]),
        center_stack_mm=float(defaults["center_stack_mm"]),
        pos_stack_mm=float(defaults["pos_stack_mm"]),
        n_l_tabs=n_tabs,
        gap_deg=float(defaults["gap_deg"]),
        l_drop_mm=float(defaults.get("l_drop_mm", 22.5)),
        sectors=sectors,
        bed_max_mm=bed,
        join_screw_od_mm=float(defaults["join_screw_od_mm"]),
        join_boss_mm=float(defaults["join_boss_mm"]),
    )


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


def mf_to_trimesh(solid: mf.Manifold) -> trimesh.Trimesh:
    raw = solid.to_mesh()
    return trimesh.Trimesh(
        vertices=np.asarray(raw.vert_properties)[:, :3],
        faces=np.asarray(raw.tri_verts),
        process=True,
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
    tm = mf_to_trimesh(solid)
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


def annular_sector_hull(
    r_in: float, r_out: float, a0_deg: float, a1_deg: float, h: float, z0: float
) -> mf.Manifold:
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
    n = max(6, int(SEG * abs(a1_deg - a0_deg) / 360.0) + 2)
    theta = np.radians(np.linspace(a0_deg, a1_deg, n))
    pts = []
    for z, r_out in ((z0, r0_out), (z1, r1_out)):
        r_in = max(r_out - wall_t, 1.0)
        pts.append(
            np.column_stack([r_out * np.cos(theta), r_out * np.sin(theta), np.full(n, z)])
        )
        pts.append(
            np.column_stack([r_in * np.cos(theta), r_in * np.sin(theta), np.full(n, z)])
        )
    return to_mf(trimesh.convex.convex_hull(np.vstack(pts)))


def wedge_solid(a0_deg: float, a1_deg: float, r_max: float, z0: float, h: float) -> mf.Manifold:
    """Pie slice including the origin — for sector boolean."""
    n = max(8, int(SEG * abs(a1_deg - a0_deg) / 360.0) + 2)
    theta = np.radians(np.linspace(a0_deg, a1_deg, n))
    arc = np.column_stack([r_max * np.cos(theta), r_max * np.sin(theta)])
    poly = np.vstack([[0.0, 0.0], arc])
    pts = []
    for z in (z0, z0 + h):
        pts.append(np.column_stack([poly, np.full(len(poly), z)]))
    return to_mf(trimesh.convex.convex_hull(np.vstack(pts)))


def build_full_bowl(spec: BowlSpec, with_jack: bool = True) -> mf.Manifold:
    r_bot = spec.bottom_od_mm / 2
    r_top = spec.skirt_od_mm / 2
    floor_r = r_bot - spec.wall_t_mm + 0.8

    # Bottom solid ring; upper wall = discrete L legs (deep çentik by construction)
    l_drop = min(spec.l_drop_mm, spec.bowl_h_mm - 7.0)
    h_ring = max(spec.bowl_h_mm - l_drop, 6.0)
    r_ring = r_bot + (r_top - r_bot) * (h_ring / spec.bowl_h_mm)
    outer = frustum_solid(r_bot, r_ring, h_ring, 0.0)
    inner = frustum_solid(
        max(r_bot - spec.wall_t_mm, 1.0),
        max(r_ring - spec.wall_t_mm, 1.0),
        h_ring + 2.0,
        -1.0,
    )
    solid = outer - inner

    seg_span = 360.0 / spec.n_l_tabs
    tab_span = seg_span - spec.gap_deg
    for i in range(spec.n_l_tabs):
        a0 = i * seg_span + spec.gap_deg / 2
        a1 = a0 + tab_span
        leg = tapered_wall_sector(
            a0, a1, h_ring, spec.flange_z0, r_ring, r_top, spec.wall_t_mm
        )
        leg_cap = annular_sector_hull(
            r_top - spec.wall_t_mm, r_top, a0, a1, spec.flange_t_mm, spec.flange_z0
        )
        seat = annular_sector_hull(
            r_top - spec.wall_t_mm,
            spec.l_od_mm / 2,
            a0,
            a1,
            spec.flange_t_mm,
            spec.flange_z0,
        )
        solid = solid + leg + leg_cap + seat

    solid = solid + cyl(floor_r, FLOOR_T_MM, 0.0)
    solid = solid + cyl(CENTER_PAD_OD_MM / 2, spec.center_pad_top_z, 0.0)

    # Always 3 position pads @ 120° (independent of print sector count)
    n_pos = 3
    for k in range(n_pos):
        phase = 2 * np.pi * k / n_pos
        px = spec.r_pos_mm * np.cos(phase)
        py = spec.r_pos_mm * np.sin(phase)
        pad = cyl(POS_PAD_OD_MM / 2, spec.pos_pad_top_z, 0.0)
        solid = solid + translate(pad, px, py)

    cuts: list[mf.Manifold] = []

    # Floor windows (avoid the 3 pos-pad rays)
    n_win = max(spec.sectors * 2, 6)
    pad_degs = [0.0, 120.0, 240.0]
    for i in range(n_win):
        ang = 2 * np.pi * i / n_win + np.pi / n_win
        deg = np.degrees(ang) % 360
        if min(abs(((deg - p + 180) % 360) - 180) for p in pad_degs) < 22:
            continue
        r0 = 34.0 * (spec.shell_id_mm / 185.0)
        r1 = floor_r - 8.0
        if r1 <= r0 + 5:
            continue
        r_c = 0.5 * (r0 + r1)
        half_w = 11.0 * (spec.shell_id_mm / 185.0)
        win = box(r1 - r0, half_w * 2, FLOOR_T_MM + 6.0, r_c, 0.0, -1.0)
        cuts.append(win.rotate([0.0, 0.0, np.degrees(ang)]))

    # Center pockets
    cuts.append(cyl(CENTER_HOLE_OD_MM / 2, spec.center_pad_top_z + 4.0, -1.0))
    cuts.append(
        cyl(
            TRIFLEX_POCKET_OD_MM / 2,
            TRIFLEX_POCKET_DEPTH_MM + 0.25,
            spec.center_pad_top_z - TRIFLEX_POCKET_DEPTH_MM,
        )
    )
    cuts.append(
        cyl(
            CENTER_PIEZO_OD_MM / 2,
            CENTER_PIEZO_DEPTH_MM + 0.15,
            spec.center_pad_top_z - CENTER_PIEZO_DEPTH_MM,
        )
    )
    for k in range(n_pos):
        phase = 2 * np.pi * k / n_pos
        px = spec.r_pos_mm * np.cos(phase)
        py = spec.r_pos_mm * np.sin(phase)
        rec = cyl(
            POS_PIEZO_OD_MM / 2,
            POS_PIEZO_DEPTH_MM + 0.15,
            spec.pos_pad_top_z - POS_PIEZO_DEPTH_MM,
        )
        cuts.append(translate(rec, px, py))
        inner = CENTER_HOLE_OD_MM / 2 + 2.0
        length = spec.r_pos_mm - inner
        g = box(length, 3.5, 1.6, inner + length / 2, 0.0, -0.1)
        cuts.append(g.rotate([0.0, 0.0, np.degrees(phase)]))

    if with_jack:
        # jack on sector-0 wall, offset from pad at 0°
        jack_ang = (360.0 / spec.sectors) * 0.5  # seam-adjacent on sector 0 → use 40° from pad
        jack_ang = 15.0  # mid of an L leg (avoid çentik gap)
        t = JACK_Z_FRAC
        r_jack = r_bot + (r_top - r_bot) * t
        jh = cyl(JACK_HOLE_OD_MM / 2, spec.wall_t_mm + 10.0, -(spec.wall_t_mm + 10.0) / 2)
        jh = jh.rotate([0.0, 90.0, 0.0])
        jh = translate(jh, r_jack - spec.wall_t_mm / 2, 0.0, spec.bowl_h_mm * t)
        cuts.append(jh.rotate([0.0, 0.0, jack_ang]))

    for c in cuts:
        solid = solid - c
    return solid


def _inner_wall_r(spec: BowlSpec, z: float) -> float:
    """Approx inner radius of tapered wall at height z."""
    t = np.clip(z / spec.bowl_h_mm, 0.0, 1.0)
    r_bot_i = spec.bottom_od_mm / 2 - spec.wall_t_mm
    r_top_i = spec.skirt_od_mm / 2 - spec.wall_t_mm
    return r_bot_i + (r_top_i - r_bot_i) * t


def add_join_features(sector: mf.Manifold, spec: BowlSpec, a0_deg: float, a1_deg: float) -> mf.Manifold:
    """Tall internal splice plates + floor lap + wall pin. Nothing outside skirt OD."""
    join_h = max(spec.bowl_h_mm - 6.0, 28.0)
    z_lo = JOIN_Z0_MM
    z_mid = z_lo + join_h / 2
    r_wall = _inner_wall_r(spec, z_mid)
    r_outer = r_wall - 0.3
    r_inner = max(r_outer - JOIN_IN_MM, 28.0)
    r_c = 0.5 * (r_outer + r_inner)
    radial_len = r_outer - r_inner

    def splice(ang_deg: float, y_inside: float) -> mf.Manifold:
        return box(
            radial_len,
            JOIN_THICK_MM,
            join_h,
            r_c,
            y_inside,
            z_lo,
        ).rotate([0.0, 0.0, ang_deg])

    sector = sector + splice(a1_deg, -JOIN_THICK_MM / 2)
    sector = sector + splice(a0_deg, +JOIN_THICK_MM / 2)

    # 3 horizontal M3 per seam face (pair up when assembled)
    for ang, y0 in ((a1_deg, -JOIN_THICK_MM / 2), (a0_deg, +JOIN_THICK_MM / 2)):
        for z_h in (z_lo + 6.0, z_mid, z_lo + join_h - 6.0):
            for r in (r_c - 3.5, r_c + 3.5):
                if r < r_inner + 2 or r > r_outer - 2:
                    continue
                hole = cyl(
                    spec.join_screw_od_mm / 2,
                    JOIN_THICK_MM + 8.0,
                    -(JOIN_THICK_MM + 8.0) / 2,
                )
                hole = hole.rotate([90.0, 0.0, 0.0])
                hole = translate(hole, r, y0, z_h).rotate([0.0, 0.0, ang])
                sector = sector - hole

    # Floor lap tabs (vertical M3) — strengthens bottom seam
    for ang, y_sign in ((a0_deg, 1.0), (a1_deg, -1.0)):
        lap = box(22.0, 10.0, FLOOR_T_MM + 1.0, r_c, y_sign * 4.0, 0.0)
        sector = sector + lap.rotate([0.0, 0.0, ang])
        vhole = cyl(spec.join_screw_od_mm / 2, FLOOR_T_MM + 6.0, -2.0)
        sector = sector - translate(vhole, r_c, y_sign * 4.0, 0.0).rotate(
            [0.0, 0.0, ang]
        )

    # Wall registration pin (inside wall thickness)
    t = 0.45
    r_wall_c = (
        spec.bottom_od_mm / 2
        + (spec.skirt_od_mm / 2 - spec.bottom_od_mm / 2) * t
        - spec.wall_t_mm / 2
    )
    pl, pt, ph = PIN_SIZE_MM
    pin_z = z_lo + 8.0
    pin = box(pl, pt + 1.0, ph, r_wall_c, -(pt / 2 + 0.5), pin_z).rotate(
        [0.0, 0.0, a1_deg]
    )
    pocket = box(
        pl + PIN_CLEAR_MM,
        pt + PIN_CLEAR_MM + 1.4,
        ph + PIN_CLEAR_MM,
        r_wall_c,
        +(pt / 2 + 0.7),
        pin_z - PIN_CLEAR_MM / 2,
    ).rotate([0.0, 0.0, a0_deg])
    sector = sector + pin
    sector = sector - pocket

    # Clip join extras outside skirt (keep L flange above)
    escaped = cyl(spec.l_od_mm / 2 + 20.0, join_h + 8.0, z_lo - 2.0) - cyl(
        spec.skirt_od_mm / 2 + 0.15, join_h + 10.0, z_lo - 3.0
    )
    sector = sector - escaped
    return sector


def extract_sector(full: mf.Manifold, spec: BowlSpec, index: int) -> mf.Manifold:
    span = 360.0 / spec.sectors
    # pad at midline index * span; seams at midline ± span/2
    mid = index * span
    a0 = mid - span / 2
    a1 = mid + span / 2
    # slight overlap so boolean doesn't leave hairline gaps at center
    wedge = wedge_solid(a0 - 0.15, a1 + 0.15, spec.l_od_mm / 2 + 8.0, -2.0, spec.mesh_z + 6.0)
    sector = full ^ wedge
    sector = add_join_features(sector, spec, a0, a1)
    return sector


def cleanup(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    parts = mesh.split(only_watertight=False)
    if len(parts) > 1:
        parts = sorted(
            parts,
            key=lambda m: float(m.volume) if m.is_volume else len(m.faces),
            reverse=True,
        )
        mesh = parts[0]
    return mesh


def export_mesh(mesh: trimesh.Trimesh, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mesh.export(path)
    size = mesh.bounds[1] - mesh.bounds[0]
    print(
        f"  {path.name}: {size[0]:.1f}×{size[1]:.1f}×{size[2]:.1f} mm  "
        f"wt={mesh.is_watertight}  faces={len(mesh.faces)}"
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="TriSense S04 modular bowl generator")
    p.add_argument("size", help="size name from cad/sizes.toml (e.g. diy8, tom14)")
    p.add_argument("--sectors", type=int, default=None, help="override sector count")
    p.add_argument("--monolith", action="store_true", help="single piece instead of sectors")
    p.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT / "models" / "experimental",
        help="output directory",
    )
    args = p.parse_args(argv)

    spec = resolve_spec(args.size, args.sectors)
    chord = spec.l_od_mm * math.sin(math.pi / spec.sectors)
    print(f"size={spec.name}  {spec.inch}\"  ID={spec.shell_id_mm}  L_OD={spec.l_od_mm}")
    print(
        f"sectors={spec.sectors}  chord≈{chord:.0f} mm  "
        f"(bed_max={spec.bed_max_mm})  mesh_z={spec.mesh_z}"
    )

    if args.monolith:
        full = build_full_bowl(spec, with_jack=True)
        mesh = cleanup(mf_to_trimesh(full))
        out = args.out_dir / f"trisense-bowl-{spec.name}-s04.stl"
        export_mesh(mesh, out)
        return 0

    # Build once with jack; sector 0 keeps it, others rebuild without… simpler: build with jack,
    # extract all; jack only falls in sector 0 if angle is inside sector 0 span.
    full = build_full_bowl(spec, with_jack=True)
    letters = "abcdefghijklmnopqrstuvwxyz"
    for i in range(spec.sectors):
        sector = extract_sector(full, spec, i)
        mesh = cleanup(mf_to_trimesh(sector))
        out = args.out_dir / f"trisense-bowl-{spec.name}-s04-{letters[i]}.stl"
        export_mesh(mesh, out)

    # small assembly note file
    note = args.out_dir / f"trisense-bowl-{spec.name}-s04-README.txt"
    note.write_text(
        f"TriSense bowl S04 — {spec.name} ({spec.inch}\")\n"
        f"Print {spec.sectors} sectors (a..). Join INSIDE the bowl:\n"
        f"  facing flanges + M3 (horizontal) + wall registration pin.\n"
        f"Nothing sticks outside the shell OD. Sector a has the jack hole.\n"
        f"L_OD={spec.l_od_mm} skirt={spec.skirt_od_mm} bottom={spec.bottom_od_mm} H={spec.mesh_z}\n"
        f"Measure shell ID before trusting catalog sizes other than diy8.\n"
    )
    print("wrote", note.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
