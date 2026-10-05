"""One-time construction of Blender/FPS_Rig.blend from Source/LowPolyMale_Rigged.fbx.

Not needed for animating. Run from the repo root:
    blender -b -P Blender/scripts/build_fps_rig.py
or  python3 Blender/scripts/build_fps_rig.py   (with the `bpy` pip module)

The Mixamo bones keep their names, hierarchy, rest pose and weights. Controls are
non-deform bones added to the same armature; deform bones only receive constraints.
See Docs/RIG_PLAN.md.
"""
import math
import os

import bpy
from mathutils import Matrix, Quaternion, Vector

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
SRC = os.path.join(REPO, "Source", "LowPolyMale_Rigged.fbx")
OUT = os.path.join(REPO, "Blender", "FPS_Rig.blend")
EXPORT_SCRIPT = os.path.join(REPO, "Blender", "scripts", "export_action_to_unity.py")

P = "mixamorig:"
SIDES = {"L": "Left", "R": "Right"}
FINGERS = ["Thumb", "Index", "Middle", "Ring", "Pinky"]
EYE_WORLD = Vector((0.0, -0.070, 1.645))  # metres: between the eyes, at the eye-surface plane

COL_CENTER, COL_LEFT, COL_RIGHT = "THEME09", "THEME04", "THEME01"
COL_FINGER, COL_CAMERA, COL_WEAPON = "THEME03", "THEME06", "THEME02"


# ---------------------------------------------------------------- scene / import
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.fps = 30
scene.render.fps_base = 1.0
scene.frame_start, scene.frame_end = 1, 60
bpy.ops.import_scene.fbx(filepath=SRC)

arm = bpy.data.objects["Armature"]
mesh = bpy.data.objects["SM_LowPolyMale"]
arm.name = "Armature"  # FBX root node name; keep stable
take = arm.animation_data.action if arm.animation_data else None
if take:
    arm.animation_data.action = None
    bpy.data.actions.remove(take)
for pb in arm.pose.bones:
    pb.matrix_basis = Matrix()

MW = arm.matrix_world.copy()
INV = MW.inverted()
INV3 = INV.to_3x3()


def L(v):
    """World-space point (metres) -> armature space."""
    return INV @ Vector(v)


def Ld(v):
    """World-space direction (metres) -> armature space."""
    return INV3 @ Vector(v)


# ---------------------------------------------------------------- widgets
wgt_col = bpy.data.collections.new("Widgets")
scene.collection.children.link(wgt_col)


def widget(name, verts, edges):
    me = bpy.data.meshes.new("WGT_" + name)
    me.from_pydata([tuple(v) for v in verts], edges, [])
    ob = bpy.data.objects.new("WGT_" + name, me)
    wgt_col.objects.link(ob)
    return ob


def ring(r, y=0.0, n=24, z0=0.0):
    vs = [(r * math.cos(2 * math.pi * i / n), y, z0 + r * math.sin(2 * math.pi * i / n)) for i in range(n)]
    return vs, [(i, (i + 1) % n) for i in range(n)]


def box(x0, x1, y0, y1, z0, z1):
    vs = [(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
    es = [(0, 1), (2, 3), (4, 5), (6, 7), (0, 2), (1, 3), (4, 6), (5, 7), (0, 4), (1, 5), (2, 6), (3, 7)]
    return vs, es


def merge(*parts):
    vs, es = [], []
    for pv, pe in parts:
        o = len(vs)
        vs += pv
        es += [(a + o, b + o) for a, b in pe]
    return vs, es


def scaled(part, s):
    return [tuple(c * s for c in v) for v in part[0]], part[1]


W = {}
W["root"] = widget("Root", *merge(ring(45), ([(-7, 0, 45), (0, 0, 60), (7, 0, 45)], [(0, 1), (1, 2)])))
W["torso"] = widget("Torso", *box(-28, 28, 0, 0, -20, 20))
W["hips"] = widget("Hips", *ring(20, y=-2))
W["spine"] = widget("Spine", *ring(17, y=5))
W["neck"] = widget("Neck", *ring(8, y=3))
W["head"] = widget("Head", *ring(13, y=12))
W["shoulder"] = widget("Shoulder", *ring(6, y=9))
W["hand"] = widget("Hand", *box(-5, 5, -1, 13, -3, 3))
W["pole"] = widget("Pole", [(4, 0, 0), (-4, 0, 0), (0, 4, 0), (0, -4, 0), (0, 0, 4), (0, 0, -4)],
                   [(0, 2), (2, 1), (1, 3), (3, 0), (0, 4), (4, 1), (1, 5), (5, 0), (2, 4), (4, 3), (3, 5), (5, 2)])
W["foot"] = widget("Foot", [(-6, -7, -10.5), (6, -7, -10.5), (6, 24, -10.5), (-6, 24, -10.5)],
                   [(0, 1), (1, 2), (2, 3), (3, 0)])
W["toe"] = widget("Toe", *ring(5, y=3))
W["finger"] = widget("Finger", *ring(1.0, y=1.5))
W["finger_master"] = widget("FingerMaster", *merge(ring(1.4, y=1.5, z0=-3.5), ([(0, 1.5, 0), (0, 1.5, -2.1)], [(0, 1)])))
W["grip"] = widget("Grip", *merge(ring(3.0, y=0, z0=-6), ([(-3, 0, -6), (3, 0, -6)], [(0, 1)])))
W["weapon"] = widget("Weapon", *box(-2, 2, -8, 45, -3, 5))
W["camera"] = widget("Camera", [(0, 0, 0), (-7, -4, 12), (7, -4, 12), (7, 4, 12), (-7, 4, 12), (-3, 5, 12), (3, 5, 12), (0, 8, 12)],
                     [(0, 1), (0, 2), (0, 3), (0, 4), (1, 2), (2, 3), (3, 4), (4, 1), (5, 6), (6, 7), (7, 5)])
wgt_col.hide_viewport = True
wgt_col.hide_render = True


# ---------------------------------------------------------------- edit bones
bpy.context.view_layer.objects.active = arm
arm.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
eb = arm.data.edit_bones
DEFORM = [b.name for b in eb]


def dup(name, src, parent=None, length=None):
    s = eb[src]
    b = eb.new(name)
    b.head, b.tail, b.roll = s.head.copy(), s.tail.copy(), s.roll
    if length:
        b.length = length
    b.parent = eb[parent] if parent else None
    b.use_deform = False
    return b


def new(name, head_w, dir_w, z_w, length_cm, parent=None):
    """Bone at world point, pointing along world dir, with local Z toward world z_w."""
    b = eb.new(name)
    b.head = L(head_w)
    b.tail = b.head + Ld(Vector(dir_w).normalized()) * (length_cm / 100.0)
    b.align_roll(Ld(Vector(z_w)))
    b.parent = eb[parent] if parent else None
    b.use_deform = False
    return b


def wpos(name):
    return MW @ eb[name].head


UP, FWD = (0, 0, 1), (0, -1, 0)

# Exported camera bone: top-level, rest orientation of the Head bone, at the eyes.
cam = eb.new("AnimCamera")
m = eb[P + "Head"].matrix.copy()
m.translation = L(EYE_WORLD)
cam.length = 10.0
cam.matrix = m
cam.use_deform = True  # no vertex group -> no skinning; kept by "Only Deform Bones"

# Body
new("CTRL_Root", (0, 0, 0), UP, FWD, 30)
dup("CTRL_Torso", P + "Hips", "CTRL_Root")
dup("CTRL_Hips", P + "Hips", "CTRL_Torso")
dup("CTRL_Spine", P + "Spine", "CTRL_Torso")
dup("CTRL_Chest", P + "Spine1", "CTRL_Spine")
dup("CTRL_UpperChest", P + "Spine2", "CTRL_Chest")
dup("CTRL_Neck", P + "Neck", "CTRL_UpperChest")
dup("CTRL_Head", P + "Head", "CTRL_Neck")

# Weapon socket at the right palm, pointing forward, Z up
rh = eb[P + "RightHand"]
grip_w = MW @ (rh.head + rh.y_axis * rh.length * 0.55 + rh.z_axis * 2.5)
new("MCH_Space_Weapon", grip_w, FWD, UP, 30)
new("CTRL_Weapon", grip_w, FWD, UP, 30, "MCH_Space_Weapon")

# Camera control
dup("MCH_Space_Camera", "AnimCamera")
dup("CTRL_Camera", "AnimCamera", "MCH_Space_Camera")

for s, side in SIDES.items():
    # Arms
    dup(f"CTRL_Shoulder.{s}", P + f"{side}Shoulder", "CTRL_UpperChest")
    dup(f"MCH_Space_Hand.{s}", P + f"{side}Hand")
    dup(f"CTRL_Hand_IK.{s}", P + f"{side}Hand", f"MCH_Space_Hand.{s}")
    elbow = wpos(P + f"{side}ForeArm")
    new(f"CTRL_Elbow_Pole.{s}", elbow + Vector((0, 0.45, 0)), UP, FWD, 5, "CTRL_UpperChest")

    # Legs: world-aligned foot control at the ankle
    ankle = wpos(P + f"{side}Foot")
    new(f"CTRL_Foot_IK.{s}", ankle, FWD, UP, 15, "CTRL_Root")
    dup(f"MCH_Foot.{s}", P + f"{side}Foot", f"CTRL_Foot_IK.{s}")
    dup(f"CTRL_Toe.{s}", P + f"{side}ToeBase", f"MCH_Foot.{s}")
    knee = wpos(P + f"{side}Leg")
    new(f"CTRL_Knee_Pole.{s}", knee + Vector((0, -0.50, 0)), UP, FWD, 5, f"CTRL_Foot_IK.{s}")

    # Fingers: master (curl/spread) + per-joint detail chain, all under the deform hand
    hand = P + f"{side}Hand"
    for f in FINGERS:
        dup(f"CTRL_{f}.{s}", P + f"{side}Hand{f}1", hand)
        parent = hand
        for i in (1, 2, 3):
            dup(f"CTRL_{f}{i}.{s}", P + f"{side}Hand{f}{i}", parent)
            parent = f"CTRL_{f}{i}.{s}"
    dup(f"CTRL_Grip.{s}", P + f"{side}HandMiddle1", hand)

bpy.ops.object.mode_set(mode="OBJECT")


# ---------------------------------------------------------------- collections / colours / shapes
coll = arm.data.collections
for c in list(coll):
    coll.remove(c)
C_MAIN = coll.new("Main")
C_FING = coll.new("Fingers")
C_DET = coll.new("Finger Detail")
C_DEF = coll.new("Deform (Mixamo)")
C_MCH = coll.new("Mechanism")
C_DET.is_visible = False
C_DEF.is_visible = False
C_MCH.is_visible = False

pbs = arm.pose.bones


def ctrl(name, shape, col, collection, rot_mode="QUATERNION", lock_loc=False, lock_rot=(False, False, False),
         wire=2.0, scale=1.0):
    pb = pbs[name]
    b = pb.bone
    collection.assign(b)
    pb.custom_shape = W[shape]
    pb.use_custom_shape_bone_size = False
    pb.custom_shape_scale_xyz = (scale, scale, scale)
    pb.custom_shape_wire_width = wire
    pb.color.palette = col
    b.color.palette = col
    pb.rotation_mode = rot_mode
    pb.lock_location = (lock_loc,) * 3
    pb.lock_rotation = lock_rot
    pb.lock_rotation_w = False
    pb.lock_scale = (True, True, True)
    return pb


for n in DEFORM + ["AnimCamera"]:
    C_DEF.assign(arm.data.bones[n])
for b in arm.data.bones:
    if b.name.startswith("MCH_"):
        C_MCH.assign(b)

ctrl("CTRL_Root", "root", COL_CENTER, C_MAIN)
ctrl("CTRL_Torso", "torso", COL_CENTER, C_MAIN, "XYZ")
ctrl("CTRL_Hips", "hips", COL_CENTER, C_MAIN, "XYZ")
for n in ("CTRL_Spine", "CTRL_Chest", "CTRL_UpperChest"):
    ctrl(n, "spine", COL_CENTER, C_MAIN, "XYZ", lock_loc=True)
ctrl("CTRL_Neck", "neck", COL_CENTER, C_MAIN, "XYZ", lock_loc=True)
ctrl("CTRL_Head", "head", COL_CENTER, C_MAIN, "XYZ", lock_loc=True)
ctrl("CTRL_Weapon", "weapon", COL_WEAPON, C_MAIN)
ctrl("CTRL_Camera", "camera", COL_CAMERA, C_MAIN, "XYZ")

for s in SIDES:
    col = COL_LEFT if s == "L" else COL_RIGHT
    ctrl(f"CTRL_Shoulder.{s}", "shoulder", col, C_MAIN, "XYZ", lock_loc=True)
    ctrl(f"CTRL_Hand_IK.{s}", "hand", col, C_MAIN)
    ctrl(f"CTRL_Elbow_Pole.{s}", "pole", col, C_MAIN, lock_rot=(True, True, True))
    ctrl(f"CTRL_Foot_IK.{s}", "foot", col, C_MAIN, "XYZ")
    ctrl(f"CTRL_Toe.{s}", "toe", col, C_MAIN, "XYZ", lock_loc=True)
    ctrl(f"CTRL_Knee_Pole.{s}", "pole", col, C_MAIN, lock_rot=(True, True, True))
    pbs[f"CTRL_Elbow_Pole.{s}"].lock_rotation_w = True
    pbs[f"CTRL_Knee_Pole.{s}"].lock_rotation_w = True
    for f in FINGERS:
        ctrl(f"CTRL_{f}.{s}", "finger_master", COL_FINGER, C_FING, "XYZ", lock_loc=True,
             lock_rot=(False, True, False))
        for i in (1, 2, 3):
            ctrl(f"CTRL_{f}{i}.{s}", "finger", col, C_DET, "XYZ", lock_loc=True, wire=1.5)
    ctrl(f"CTRL_Grip.{s}", "grip", COL_FINGER, C_FING, "XYZ", lock_loc=True, lock_rot=(False, True, True))

arm.data.display_type = "OCTAHEDRAL"
arm.show_in_front = True


# ---------------------------------------------------------------- constraints
def copy_rot(owner, target, space="WORLD", mix="REPLACE", axes=(True, True, True), name=None):
    c = pbs[owner].constraints.new("COPY_ROTATION")
    c.target, c.subtarget = arm, target
    c.owner_space = c.target_space = space
    c.mix_mode = mix
    c.use_x, c.use_y, c.use_z = axes
    if name:
        c.name = name
    return c


def copy_tr(owner, target):
    c = pbs[owner].constraints.new("COPY_TRANSFORMS")
    c.target, c.subtarget = arm, target
    c.owner_space = c.target_space = "WORLD"
    return c


def add_prop(bone, prop, default, desc):
    pb = pbs[bone]
    pb[prop] = default
    pb.id_properties_ui(prop).update(min=0.0, max=1.0, soft_min=0.0, soft_max=1.0, default=default,
                                     description=desc)


def space_switch(space_bone, targets, ctrl_bone, prop):
    """Armature constraint blending between targets[0] (prop=0) and targets[1] (prop=1)."""
    c = pbs[space_bone].constraints.new("ARMATURE")
    c.name = "Space"
    c.use_deform_preserve_volume = True
    for i, t in enumerate(targets):
        tg = c.targets.new()
        tg.target, tg.subtarget = arm, t
        fc = arm.driver_add(f'pose.bones["{space_bone}"].constraints["Space"].targets[{i}].weight')
        d = fc.driver
        d.type = "SCRIPTED"
        v = d.variables.new()
        v.name, v.type = "w", "SINGLE_PROP"
        v.targets[0].id_type = "OBJECT"
        v.targets[0].id = arm
        v.targets[0].data_path = f'pose.bones["{ctrl_bone}"]["{prop}"]'
        d.expression = "w" if i == 1 else "1 - w"


# body
copy_tr(P + "Hips", "CTRL_Hips")
for d, c in (("Spine", "CTRL_Spine"), ("Spine1", "CTRL_Chest"), ("Spine2", "CTRL_UpperChest"),
             ("Neck", "CTRL_Neck"), ("Head", "CTRL_Head")):
    copy_rot(P + d, c)

# camera / weapon
add_prop("CTRL_Camera", "Follow Head", 0.0, "0 = camera offset only from this control, 1 = camera also follows the head")
space_switch("MCH_Space_Camera", ["CTRL_Root", P + "Head"], "CTRL_Camera", "Follow Head")
copy_tr("AnimCamera", "CTRL_Camera")
add_prop("CTRL_Weapon", "Follow Chest", 1.0, "0 = weapon stays in world/root space, 1 = weapon moves with the upper body")
space_switch("MCH_Space_Weapon", ["CTRL_Root", "CTRL_UpperChest"], "CTRL_Weapon", "Follow Chest")

ik = {}
for s, side in SIDES.items():
    copy_rot(P + f"{side}Shoulder", f"CTRL_Shoulder.{s}")

    add_prop(f"CTRL_Hand_IK.{s}", "Follow Weapon", 1.0, "0 = hand stays in world/root space, 1 = hand moves with the weapon")
    space_switch(f"MCH_Space_Hand.{s}", ["CTRL_Root", "CTRL_Weapon"], f"CTRL_Hand_IK.{s}", "Follow Weapon")
    c = pbs[P + f"{side}ForeArm"].constraints.new("IK")
    c.target, c.subtarget = arm, f"CTRL_Hand_IK.{s}"
    c.pole_target, c.pole_subtarget = arm, f"CTRL_Elbow_Pole.{s}"
    c.chain_count, c.use_stretch = 2, False
    ik[f"arm.{s}"] = (c, P + f"{side}ForeArm")
    copy_rot(P + f"{side}Hand", f"CTRL_Hand_IK.{s}")

    c = pbs[P + f"{side}Leg"].constraints.new("IK")
    c.target, c.subtarget = arm, f"CTRL_Foot_IK.{s}"
    c.pole_target, c.pole_subtarget = arm, f"CTRL_Knee_Pole.{s}"
    c.chain_count, c.use_stretch = 2, False
    ik[f"leg.{s}"] = (c, P + f"{side}Leg")
    copy_rot(P + f"{side}Foot", f"MCH_Foot.{s}")
    copy_rot(P + f"{side}ToeBase", f"CTRL_Toe.{s}")

    for f in FINGERS:
        for i in (1, 2, 3):
            det = f"CTRL_{f}{i}.{s}"
            # curl (X) on every joint, spread (Z) on the first joint only
            copy_rot(det, f"CTRL_{f}.{s}", "LOCAL", "ADD", (True, False, i == 1), "Curl")
            if f != "Thumb":
                copy_rot(det, f"CTRL_Grip.{s}", "LOCAL", "ADD", (True, False, False), "Grip")
            copy_rot(P + f"{side}Hand{f}{i}", det, "LOCAL")


# ---------------------------------------------------------------- solve pole angles so rest stays rest
def rot_err(bone):
    bpy.context.view_layer.update()
    a = pbs[bone].matrix.to_quaternion()
    b = arm.data.bones[bone].matrix_local.to_quaternion()
    return a.rotation_difference(b).angle


for key, (c, bone) in ik.items():
    best = min(range(-180, 181), key=lambda d: (setattr(c, "pole_angle", math.radians(d)), rot_err(bone))[1])
    lo, hi = best - 1.0, best + 1.0
    for _ in range(40):  # golden-section refine
        m1, m2 = lo + (hi - lo) * 0.382, lo + (hi - lo) * 0.618
        c.pole_angle = math.radians(m1); e1 = rot_err(bone)
        c.pole_angle = math.radians(m2); e2 = rot_err(bone)
        if e1 < e2:
            hi = m2
        else:
            lo = m1
    c.pole_angle = math.radians((lo + hi) / 2)
    print(f"pole angle {key}: {math.degrees(c.pole_angle):.2f} deg, residual {math.degrees(rot_err(bone)):.4f} deg")


# ---------------------------------------------------------------- preview cameras / weapon reference
def parent_to_bone(ob, bone, world):
    ob.parent, ob.parent_type, ob.parent_bone = arm, "BONE", bone
    bpy.context.view_layer.update()
    ob.matrix_world = world


cd = bpy.data.cameras.new("FPS_View")
cd.sensor_fit, cd.lens_unit = "VERTICAL", "FOV"
cd.angle_y = math.radians(60.0)
cd.clip_start, cd.clip_end = 0.01, 500.0
fps_cam = bpy.data.objects.new("FPS_View", cd)
scene.collection.objects.link(fps_cam)
bm = MW @ arm.data.bones["AnimCamera"].matrix_local
loc, rot, _ = bm.decompose()
parent_to_bone(fps_cam, "AnimCamera", Matrix.LocRotScale(loc, rot @ Quaternion((0, 1, 0), math.pi), Vector((1, 1, 1))))

ed = bpy.data.cameras.new("External_View")
ed.lens = 50
ext_cam = bpy.data.objects.new("External_View", ed)
scene.collection.objects.link(ext_cam)
ext_cam.location = (2.3, -3.1, 1.05)
ext_cam.rotation_euler = (math.radians(86), 0, math.radians(36.5))
ed.lens = 35
scene.camera = fps_cam
scene.render.resolution_x, scene.render.resolution_y = 1920, 1080

# Placeholder weapon (rifle-like blocks) in world space at rest, then parented to CTRL_Weapon
g = MW @ arm.data.bones["CTRL_Weapon"].head_local
parts = [  # (center offset from grip (x, y, z) metres, size)
    ((0, -0.10, 0.06), (0.04, 0.30, 0.07)),   # receiver
    ((0, -0.42, 0.075), (0.02, 0.36, 0.02)),  # barrel
    ((0, 0.17, 0.05), (0.035, 0.24, 0.08)),   # stock
    ((0, 0.0, -0.01), (0.03, 0.04, 0.10)),    # pistol grip
    ((0, -0.08, 0.0), (0.025, 0.04, 0.09)),   # magazine
    ((0, -0.26, 0.035), (0.035, 0.14, 0.045)),  # handguard
]
verts, faces = [], []
for (cx, cy, cz), (sx, sy, sz) in parts:
    o = len(verts)
    for dx in (-0.5, 0.5):
        for dy in (-0.5, 0.5):
            for dz in (-0.5, 0.5):
                verts.append((g.x + cx + dx * sx, g.y + cy + dy * sy, g.z + cz + dz * sz))
    faces += [(o + a, o + b, o + c, o + d) for a, b, c, d in
              ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3))]
wme = bpy.data.meshes.new("REF_Weapon")
wme.from_pydata(verts, [], faces)
weapon = bpy.data.objects.new("REF_Weapon", wme)
scene.collection.objects.link(weapon)
weapon.color = (0.9, 0.45, 0.1, 1.0)
parent_to_bone(weapon, "CTRL_Weapon", Matrix())
weapon.hide_select = True

# ---------------------------------------------------------------- final rest check
bpy.context.view_layer.update()
worst = max((pbs[n].matrix.to_quaternion().rotation_difference(arm.data.bones[n].matrix_local.to_quaternion()).angle,
             n) for n in DEFORM + ["AnimCamera"])
worst_loc = max(((pbs[n].matrix.translation - arm.data.bones[n].matrix_local.translation).length, n)
                for n in DEFORM + ["AnimCamera"])
print(f"rest check: max rotation error {math.degrees(worst[0]):.4f} deg ({worst[1]}), "
      f"max location error {worst_loc[0]:.4f} cm ({worst_loc[1]})")

# ---------------------------------------------------------------- example Action: FPS ready pose
def set_world(name, pos, y=None, z=None):
    """Pose a control at a world position; optional local Y/Z toward world directions."""
    bpy.context.view_layer.update()
    pb = pbs[name]
    cur = MW @ pb.matrix
    rot = cur.to_3x3().normalized()
    if y is not None:
        Y = Vector(y).normalized()
        Z = (Vector(z) - Vector(z).project(Y)).normalized()
        rot = Matrix((Y.cross(Z), Y, Z)).transposed()
    rot_arm = (INV3 @ rot).normalized()
    pb.matrix = Matrix.LocRotScale(INV @ Vector(pos), rot_arm.to_quaternion(), Vector((1, 1, 1)))
    bpy.context.view_layer.update()


pbs["CTRL_Chest"].rotation_euler = (0, math.radians(-8), 0)
pbs["CTRL_UpperChest"].rotation_euler = (0, math.radians(-10), 0)
pbs["CTRL_Shoulder.L"].rotation_euler = (0, 0, math.radians(12))
grip = Vector((-0.11, -0.30, 1.47))
set_world("CTRL_Weapon", grip)
yr = Vector((0.25, -0.9, 0.25)).normalized()
zr = Vector((1, 0.2, 0)); zr = (zr - zr.project(yr)).normalized()
set_world("CTRL_Hand_IK.R", grip - yr * 0.066 - zr * 0.025, yr, zr)
yl = Vector((-0.8, -0.5, 0.15)).normalized()
zl = Vector((0, 0, 1)); zl = (zl - zl.project(yl)).normalized()
set_world("CTRL_Hand_IK.L", grip + Vector((0, -0.19, 0)) - yl * 0.06 - zl * 0.035, yl, zl)
set_world("CTRL_Elbow_Pole.R", (-0.55, 0.0, 0.95))
set_world("CTRL_Elbow_Pole.L", (0.45, -0.25, 0.85))
pbs["CTRL_Grip.R"].rotation_euler = (math.radians(65), 0, 0)
pbs["CTRL_Index.R"].rotation_euler = (math.radians(-45), 0, 0)
pbs["CTRL_Thumb.R"].rotation_euler = (math.radians(25), 0, 0)
pbs["CTRL_Grip.L"].rotation_euler = (math.radians(45), 0, 0)
pbs["CTRL_Thumb.L"].rotation_euler = (math.radians(15), 0, 0)
bpy.context.view_layer.update()

arm.animation_data_create()
example = bpy.data.actions.new("Example_FPS_Ready")
example.use_fake_user = True
arm.animation_data.action = example
for pb in pbs:
    if not pb.name.startswith("CTRL_"):
        continue
    for f in (1, 30):
        pb.keyframe_insert("location", frame=f)
        pb.keyframe_insert("rotation_quaternion" if pb.rotation_mode == "QUATERNION" else "rotation_euler", frame=f)
example.use_frame_range = True
example.frame_start, example.frame_end = 1, 30
scene.frame_start, scene.frame_end = 1, 30
scene.frame_set(1)
print("example reach error R %.4f m, L %.4f m" % (
    ((MW @ pbs[P + "RightHand"].head) - (MW @ pbs["CTRL_Hand_IK.R"].head)).length,
    ((MW @ pbs[P + "LeftHand"].head) - (MW @ pbs["CTRL_Hand_IK.L"].head)).length))

# Embed the export helper as a text block
if os.path.exists(EXPORT_SCRIPT):
    t = bpy.data.texts.new("export_action_to_unity.py")
    t.from_string(open(EXPORT_SCRIPT).read())

# Tidy selection: armature active in pose mode
for o in bpy.data.objects:
    o.select_set(False)
arm.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode="POSE")
bpy.ops.pose.select_all(action="DESELECT")
bpy.ops.object.mode_set(mode="OBJECT")

bpy.ops.wm.save_as_mainfile(filepath=OUT, compress=True)
print("saved", OUT)
