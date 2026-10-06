"""Prepare the M1911 from 3ds Max for the rig: part names, trigger/hammer split, pivots, effect points.

    python3 Blender/scripts/prepare_m1911.py [input.fbx]

Input (default): Source/Weapons/M1911_original_max.fbx - the model as exported from 3ds Max.
Output: Source/Weapons/M1911.fbx - the prepared parts (cm, Y-up, no rig), readable by 3ds Max and
used by build_fps_rig.py. Run it again on a new Max export; steps already done in Max are skipped:
- parts renamed to M1911_<Part> (Pistol_<Part> is accepted);
- M1911_Hammer split from the frame (faces with the "Hammer" material), pivot at the hammer pin;
- M1911_Trigger split from the frame (the thin loose piece inside the trigger guard), it slides back;
- M1911_Magazine pivot at the top of the magazine, tilted with the grip;
- M1911_Slide pivot at its centre, M1911_Frame pivot at the grip origin;
- M1911_Muzzle / M1911_Eject empties (muzzle on the bore axis, ejection port on the right side, -X).
Modelling frame (same as the Max scene): barrel -Y, up +Z, grip point at the origin.
"""
import math
import os
import sys

import bpy  # noqa: I001  (bpy first: it makes bmesh/mathutils importable)
import bmesh
from mathutils import Matrix, Vector

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRC = sys.argv[-1] if sys.argv[-1].lower().endswith(".fbx") else os.path.join(REPO, "Source", "Weapons",
                                                                              "M1911_original_max.fbx")
OUT = os.path.join(REPO, "Source", "Weapons", "M1911.fbx")
W = "M1911"


def world_points(o):
    return [o.matrix_world @ v.co for v in o.data.vertices]


def bounds(pts):
    return (Vector([min(p[i] for p in pts) for i in range(3)]), Vector([max(p[i] for p in pts) for i in range(3)]))


def set_pivot(o, pivot):
    """Move the object origin to the world matrix `pivot` (no scale) without moving the mesh."""
    mw = o.matrix_world.copy()
    o.data.transform(pivot.inverted() @ mw)
    o.matrix_world = pivot


def bake_scale(o):
    """Bake object scale (Max cm export: 0.01) into the mesh; keep location/rotation."""
    loc, rot, _ = o.matrix_world.decompose()
    set_pivot(o, Matrix.LocRotScale(loc, rot, Vector((1, 1, 1))))


def islands(bm, faces):
    faces, seen, out = set(faces), set(), []
    for f in faces:
        if f in seen:
            continue
        stack, isl = [f], []
        seen.add(f)
        while stack:
            g = stack.pop()
            isl.append(g)
            for e in g.edges:
                for h in e.link_faces:
                    if h in faces and h not in seen:
                        seen.add(h)
                        stack.append(h)
        out.append(isl)
    return out


def split(frame, name, pick):
    """Separate the faces chosen by pick(bm) -> faces from the frame into a new object `name`."""
    bm = bmesh.new()
    bm.from_mesh(frame.data)
    chosen = set(pick(bm))
    if not chosen:
        bm.free()
        raise RuntimeError(f"{name}: nothing found to split from the frame")
    bm.faces.index_update()
    idx = {f.index for f in chosen}
    new_bm = bm.copy()
    # remove chosen from the frame, keep only chosen in the new part
    bmesh.ops.delete(bm, geom=list(chosen), context="FACES")
    new_bm.faces.ensure_lookup_table()
    bmesh.ops.delete(new_bm, geom=[f for f in new_bm.faces if f.index not in idx], context="FACES")
    bm.to_mesh(frame.data)
    me = bpy.data.meshes.new(name)
    new_bm.to_mesh(me)
    for m in frame.data.materials:
        me.materials.append(m)
    bm.free()
    new_bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.matrix_world = frame.matrix_world.copy()
    return ob


# ---------------------------------------------------------------- import
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=SRC)
for o in list(bpy.data.objects):
    for prefix in ("Pistol_", "M1911_"):
        if o.name.startswith(prefix):
            o.name = W + "_" + o.name[len(prefix):]
parts = {o.name[len(W) + 1:]: o for o in bpy.data.objects if o.name.startswith(W + "_")}
for o in parts.values():
    o.parent = None if o.type == "MESH" else o.parent
    if o.type == "MESH":
        o.matrix_world = o.matrix_world.copy()
        bake_scale(o)
frame = parts.get("Frame") or parts.get("Body") or parts.get("Receiver")
if frame is None:
    raise RuntimeError("No M1911_Frame / _Body / _Receiver in " + SRC)
frame_mats = [m.name if m else "" for m in frame.data.materials]

# ---------------------------------------------------------------- hammer (material "Hammer")
if "Hammer" not in parts and "Hammer" in frame_mats:
    hi = frame_mats.index("Hammer")
    parts["Hammer"] = split(frame, f"{W}_Hammer", lambda bm: [f for f in bm.faces if f.material_index == hi])
    pts = world_points(parts["Hammer"])
    lo, hi_ = bounds(pts)
    base = [p for p in pts if p.z < lo.z + 0.005]
    pin = Vector((0.0, sum(p.y for p in base) / len(base), lo.z + 0.0035))  # pin through the lower hammer
    set_pivot(parts["Hammer"], Matrix.Translation(pin))

# ---------------------------------------------------------------- trigger (thin piece inside the guard)
if "Trigger" not in parts:
    def pick_trigger(bm):
        M = frame.matrix_world
        best = []
        for isl in islands(bm, bm.faces):
            pts = [M @ v.co for f in isl for v in f.verts]
            lo, hi = bounds(pts)
            c = (lo + hi) / 2
            thin = hi.x - lo.x < 0.007 and abs(c.x) < 0.002
            in_guard = -0.09 < c.y < -0.02 and -0.01 < c.z < 0.035 and hi.z - lo.z > 0.015
            if thin and in_guard and len(isl) > len(best):
                best = isl
        return best
    parts["Trigger"] = split(frame, f"{W}_Trigger", pick_trigger)
    pts = world_points(parts["Trigger"])
    lo, hi = bounds(pts)
    set_pivot(parts["Trigger"], Matrix.Translation(Vector((0.0, (lo.y + hi.y) / 2, hi.z))))

# ---------------------------------------------------------------- pivots: frame at the grip origin, slide centred
set_pivot(frame, Matrix())
if "Slide" in parts:
    lo, hi = bounds(world_points(parts["Slide"]))
    set_pivot(parts["Slide"], Matrix.Translation(Vector((0.0, (lo.y + hi.y) / 2, (lo.z + hi.z) / 2))))

# ---------------------------------------------------------------- magazine: pivot on top, tilted with the grip
if "Magazine" in parts:
    mag = parts["Magazine"]
    pts = world_points(mag)
    c = sum(pts, Vector()) / len(pts)
    # long axis (power iteration on the covariance), pointing up
    cov = [[sum((p[i] - c[i]) * (p[j] - c[j]) for p in pts) for j in range(3)] for i in range(3)]
    ax = Vector((0, 0, 1))
    for _ in range(50):
        ax = Vector([sum(cov[i][j] * ax[j] for j in range(3)) for i in range(3)]).normalized()
    if ax.z < 0:
        ax = -ax
    tilt = math.atan2(-ax.y, ax.z)  # rotation about X that takes +Z onto the magazine axis
    rot = Matrix.Rotation(tilt, 4, "X")
    top = max((p - c).dot(ax) for p in pts)
    set_pivot(mag, Matrix.Translation(Vector((0.0, c.y, c.z)) + ax * top) @ rot)
    print(f"magazine tilt {math.degrees(tilt):.1f} deg")

# ---------------------------------------------------------------- effect points
fpts = world_points(frame)
slide_pts = world_points(parts["Slide"]) if "Slide" in parts else fpts
front = min(p.y for p in fpts + slide_pts)
bore = [p for p in fpts + slide_pts if p.y < front + 0.0025]
muzzle = Vector((0.0, front, sum(p.z for p in bore) / len(bore)))
slo, shi = bounds(slide_pts)
for name, loc in (("Muzzle", muzzle), ("Eject", Vector((slo.x, -0.065, slo.z + 0.6 * (shi.z - slo.z))))):
    old = parts.get(name)
    if old is None:
        e = bpy.data.objects.new(f"{W}_{name}", None)
        bpy.context.scene.collection.objects.link(e)
        e.empty_display_type, e.empty_display_size = "ARROWS", 0.01
        e.location = loc
        parts[name] = e

# ---------------------------------------------------------------- export (cm, Y-up like 3ds Max)
for o in bpy.data.objects:
    o.select_set(o.name.startswith(W + "_"))
bpy.ops.export_scene.fbx(filepath=OUT, use_selection=True, object_types={"MESH", "EMPTY"},
                         apply_scale_options="FBX_SCALE_UNITS", axis_forward="-Z", axis_up="Y",
                         bake_anim=False, add_leaf_bones=False, mesh_smooth_type="FACE")
for n in sorted(parts):
    o = parts[n]
    info = f"{len(o.data.polygons)} faces" if o.type == "MESH" else "empty"
    print(f"{o.name:16s} pivot (cm) {tuple(round(v * 100, 2) for v in o.matrix_world.translation)}  {info}")
print("saved", OUT)
