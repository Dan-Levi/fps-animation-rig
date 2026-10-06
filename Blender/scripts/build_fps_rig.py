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
import sys

import bpy
from mathutils import Matrix, Quaternion, Vector

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
SRC = os.path.join(REPO, "Source", "LowPolyMale_Rigged.fbx")
OUT = os.path.join(REPO, "Blender", "FPS_Rig.blend")
TOOLS_SCRIPT = os.path.join(REPO, "Blender", "scripts", "fps_rig_tools.py")
sys.path.insert(0, os.path.dirname(TOOLS_SCRIPT))
import fps_rig_tools as tools  # noqa: E402  (shared keying / switch / export logic)

P = "mixamorig:"
SIDES = {"L": "Left", "R": "Right"}
FINGERS = ["Thumb", "Index", "Middle", "Ring", "Pinky"]
EYE_WORLD = Vector((0.0, -0.070, 1.645))  # metres: between the eyes, at the eye-surface plane
# Right-hand pistol grip, in weapon space (weapon barrel = -Y, up = +Z, pivot at the grip):
# hand bone Y (wrist -> knuckles) and palm normal (+Z), and wrist offset (along Y, along Z) in metres.
GRIP_HAND_Y = (0.25, -0.9, 0.25)
GRIP_HAND_Z = (1.0, 0.2, 0.0)
GRIP_PALM = (0.066, 0.025)
# Grip Z fan spread per finger: (amount, moves toward thumb side)
FAN = {"Index": (1.0, True), "Middle": (0.3, True), "Ring": (0.5, False), "Pinky": (1.0, False)}
# Grip / finger curl share per joint (knuckle, middle, tip): the tip joint bends less, like a real fist
CURL_SPLIT = (1.0, 1.0, 0.7)
# Thumb curl aims across the palm at this point: between the middle and ring knuckles, this far into the palm (m)
THUMB_TARGET_DEPTH = 0.02

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
take = arm.animation_data.action if arm.animation_data else None
if take:
    arm.animation_data.action = None
    bpy.data.actions.remove(take)
for pb in arm.pose.bones:
    pb.matrix_basis = Matrix()

# Apply the FBX's 0.01 scale (armature + mesh) so the rig works in metres: pose values in the
# sidebar are real metres. The X 90 deg rotation stays (it cancels the FBX axis conversion).
for o in bpy.data.objects:
    o.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

mesh_obj = bpy.data.objects["SM_LowPolyMale"]
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


WGT_UNIT = 0.01  # widgets below are modelled in centimetres
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
cam.length = 0.10
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

# Weapon socket: the runtime attachment point, rigidly on the right hand (as a Unity hand
# socket would be). The grip offset is defined by a pistol-grip hand pose relative to a
# weapon pointing forward with its pivot at the grip.
def frame(y, z):
    Y = Vector(y).normalized()
    Z = (Vector(z) - Vector(z).project(Y)).normalized()
    return Matrix((Y.cross(Z), Y, Z)).transposed()


grip_hand_rot = frame(GRIP_HAND_Y, GRIP_HAND_Z)
grip_hand = Matrix.Translation(-(grip_hand_rot.col[1] * GRIP_PALM[0] + grip_hand_rot.col[2] * GRIP_PALM[1])) \
    @ grip_hand_rot.to_4x4()                                  # hand in weapon-grip space
socket_axes = frame(UP, FWD).to_4x4()                         # socket: Y = weapon up, Z = barrel
socket_in_hand = grip_hand.inverted() @ socket_axes
rh = eb[P + "RightHand"]
rh_world = MW @ rh.matrix
rh_world = Matrix.LocRotScale(rh_world.translation, rh_world.to_quaternion(), Vector((1, 1, 1)))
socket_world = rh_world @ socket_in_hand
sock = eb.new("WPN_Socket")
sock.length = 0.08
sock.matrix = Matrix.LocRotScale(INV @ socket_world.translation, (INV3 @ socket_world.to_3x3()).normalized().to_quaternion(),
                                 Vector((1, 1, 1)))
sock.parent = rh
sock.use_deform = False
# Left-hand prop socket (mirror of the right-hand grip): magazines/props held in the left hand follow it
lh = eb[P + "LeftHand"]
lh_world = MW @ lh.matrix
lh_world = Matrix.LocRotScale(lh_world.translation, lh_world.to_quaternion(), Vector((1, 1, 1)))
_mirror = Matrix.Diagonal((-1.0, 1.0, 1.0, 1.0))
prop_world = lh_world @ (_mirror @ socket_in_hand.inverted() @ _mirror).inverted()
prop_l = eb.new("PROP_Hand.L")
prop_l.length = 0.06
prop_l.matrix = Matrix.LocRotScale(INV @ prop_world.translation, (INV3 @ prop_world.to_3x3()).normalized().to_quaternion(),
                                   Vector((1, 1, 1)))
prop_l.parent = lh
prop_l.use_deform = False
grip_w = socket_world.translation
barrel_w, up_w = socket_world.to_3x3().col[2], socket_world.to_3x3().col[1]
new("MCH_Space_Weapon", grip_w, barrel_w, up_w, 30)
new("CTRL_Weapon", grip_w, barrel_w, up_w, 30, "MCH_Space_Weapon")

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

    # Thumb: Mixamo gives it the same roll as the fingers, so X would fold it down under the palm.
    # Its controls get a roll whose +Z (where +X curls toward) points across the palm; the MCH bones
    # keep the deform roll and pass the rotation on, so the deform skeleton stays untouched.
    palm = eb[hand].z_axis  # hand +Z = palm side
    target = (eb[P + f"{side}HandMiddle1"].head + eb[P + f"{side}HandRing1"].head) / 2 + palm * THUMB_TARGET_DEPTH
    across = target - eb[P + f"{side}HandThumb2"].head
    for n in [f"CTRL_Thumb.{s}"] + [f"CTRL_Thumb{i}.{s}" for i in (1, 2, 3)]:
        eb[n].align_roll(across)
    for i in (1, 2, 3):
        dup(f"MCH_Thumb{i}.{s}", P + f"{side}HandThumb{i}", f"CTRL_Thumb{i}.{s}")

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
    pb.custom_shape_scale_xyz = (scale * WGT_UNIT,) * 3
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
    if b.name.startswith("MCH_") or b.name in ("WPN_Socket", "PROP_Hand.L"):
        C_MCH.assign(b)

ctrl("CTRL_Root", "root", COL_CENTER, C_MAIN)
ctrl("CTRL_Torso", "torso", COL_CENTER, C_MAIN, "XYZ")
ctrl("CTRL_Hips", "hips", COL_CENTER, C_MAIN, "XYZ", lock_loc=True)
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
    ctrl(f"CTRL_Grip.{s}", "grip", COL_FINGER, C_FING, "XYZ", lock_loc=True, lock_rot=(False, True, False))

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
    # Right hand carries the weapon (driven by CTRL_Weapon); the left hand follows the weapon as it
    # actually sits in the right hand, so both hands agree with a runtime right-hand socket.
    space_switch(f"MCH_Space_Hand.{s}", ["CTRL_Root", "CTRL_Weapon" if s == "R" else "WPN_Socket"],
                 f"CTRL_Hand_IK.{s}", "Follow Weapon")
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
            # curl (X) on every joint, side-to-side (Z) on the first joint only
            c = copy_rot(det, f"CTRL_{f}.{s}", "LOCAL", "ADD", (True, False, i == 1), "Curl")
            if f == "Thumb" and i == 1:
                c.influence = 0.5  # thumb metacarpal moves less than the thumb joints
                c.invert_z = s == "L"  # thumb Z: + spreads the thumb away from the palm on both hands
            if f != "Thumb":
                c.influence = CURL_SPLIT[i - 1]
                g = copy_rot(det, f"CTRL_Grip.{s}", "LOCAL", "ADD", (True, False, False), "Grip")
                g.influence = CURL_SPLIT[i - 1]
                if i == 1:
                    # Grip Z = fan spread: +Z opens the hand on both sides
                    amount, toward_thumb = FAN[f]
                    c = copy_rot(det, f"CTRL_Grip.{s}", "LOCAL", "ADD", (False, False, True), "Grip Spread")
                    c.influence = amount
                    # local +Z moves fingers toward the thumb on the left hand, toward the pinky on the right
                    c.invert_z = toward_thumb != (s == "L")
            if f == "Thumb":  # rolled control: hand the rotation over through the deform-rolled MCH bone
                copy_rot(P + f"{side}Hand{f}{i}", f"MCH_Thumb{i}.{s}")
            else:
                copy_rot(P + f"{side}Hand{f}{i}", det, "LOCAL")


# ---------------------------------------------------------------- solve pole angles so rest stays rest
def rot_err(bones):
    bpy.context.view_layer.update()
    return sum(pbs[b].matrix.to_quaternion().rotation_difference(arm.data.bones[b].matrix_local.to_quaternion()).angle
               for b in bones)


for key, (c, bone) in ik.items():
    chain = [bone, pbs[bone].parent.name]
    best = 0.0
    for span, step in ((180.0, 1.0), (1.0, 0.05), (0.05, 0.002)):  # nested grid search
        n = int(round(span / step))
        cands = [best + i * step for i in range(-n, n + 1)]
        best = min(cands, key=lambda d: (setattr(c, "pole_angle", math.radians(d)), rot_err(chain))[1])
    c.pole_angle = math.radians(best)
    bone = chain
    print(f"pole angle {key}: {math.degrees(c.pole_angle):.3f} deg, residual {math.degrees(rot_err(bone)):.4f} deg")


# ---------------------------------------------------------------- preview cameras / weapon reference
def parent_to_bone(ob, bone, world):
    ob.parent, ob.parent_type, ob.parent_bone = arm, "BONE", bone
    bpy.context.view_layer.update()
    ob.matrix_world = world


cd = bpy.data.cameras.new("FPS_View")
cd.sensor_fit, cd.lens_unit = "VERTICAL", "FOV"
cd.angle_y = math.radians(60.0)
cd.clip_start, cd.clip_end = 0.01, 500.0
cd.show_composition_center = True  # centre cross = where the gameplay crosshair is
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

# ---------------------------------------------------------------- weapon references
# Visible attach point for weapon models: origin = grip, Z arrow = barrel/business end, Y arrow = up.
sm = MW @ arm.data.bones["WPN_Socket"].matrix_local
attach = bpy.data.objects.new("WPN_Attach", None)
attach.empty_display_type, attach.empty_display_size = "ARROWS", 0.08
scene.collection.objects.link(attach)
parent_to_bone(attach, "WPN_Socket", Matrix.LocRotScale(sm.translation, sm.to_quaternion(), Vector((1, 1, 1))))

weapons_col = bpy.data.collections.new(tools.WEAPONS_COLLECTION)
scene.collection.children.link(weapons_col)


def box_mesh(name, parts, origin=(0, 0, 0)):
    """Mesh from boxes (center, size) in metres, vertices relative to origin."""
    ox, oy, oz = origin
    verts, faces = [], []
    for (cx, cy, cz), (sx, sy, sz) in parts:
        o = len(verts)
        for dx in (-0.5, 0.5):
            for dy in (-0.5, 0.5):
                for dz in (-0.5, 0.5):
                    verts.append((cx + dx * sx - ox, cy + dy * sy - oy, cz + dz * sz - oz))
        faces += [(o + a, o + b, o + c, o + d) for a, b, c, d in
                  ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3))]
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    return me


def blocks(name, parts, color):
    """Unrigged placeholder in socket space (center (x, up, forward), size), in its own Weapons/REF_ collection."""
    col = bpy.data.collections.new(name)
    weapons_col.children.link(col)
    ob = bpy.data.objects.new(name, box_mesh(name, parts))
    col.objects.link(ob)
    ob.color = color
    ob.parent = attach
    ob.hide_select = True
    return ob


def model_part(name, parts, origin, color, parent=None):
    """A weapon part modelled like in 3ds Max: modelling space (barrel -Y, up +Z, grip at the origin),
    object origin = the part's pivot. parts: (center (x, y, z), size) in metres."""
    ob = bpy.data.objects.new(name, box_mesh(name, parts, origin))
    scene.collection.objects.link(ob)
    ob.location = origin
    ob.color = color
    if parent:
        ob.parent = parent
        ob.matrix_parent_inverse = parent.matrix_world.inverted()
    return ob


def model_empty(name, location):
    ob = bpy.data.objects.new(name, None)
    scene.collection.objects.link(ob)
    ob.location = location
    return ob


ORANGE, GREY, DARK, BROWN, STEEL, GOLD = (0.9, 0.45, 0.1, 1), (0.25, 0.25, 0.28, 1), (0.12, 0.12, 0.14, 1), \
    (0.55, 0.35, 0.2, 1), (0.45, 0.5, 0.55, 1), (0.85, 0.7, 0.2, 1)

# Rigged placeholder pistol (Frame, Slide, Trigger, Magazine + Muzzle/Eject), built with the panel's tool
PISTOL_PARTS = [
    model_part("Pistol_Frame", [((0, 0.005, -0.005), (0.028, 0.045, 0.11)), ((0, -0.075, 0.035), (0.026, 0.13, 0.025)),
                                ((0, -0.045, 0.006), (0.008, 0.045, 0.006))], (0, 0, 0), GREY),
    model_part("Pistol_Slide", [((0, -0.06, 0.065), (0.03, 0.19, 0.035)), ((0, -0.145, 0.086), (0.004, 0.006, 0.007)),
                                ((0, 0.025, 0.086), (0.02, 0.006, 0.007))], (0, -0.06, 0.065), DARK),
    model_part("Pistol_Trigger", [((0, -0.038, 0.013), (0.006, 0.008, 0.024))], (0, -0.036, 0.026), DARK),
    model_part("Pistol_Magazine", [((0, 0.008, -0.012), (0.022, 0.034, 0.11)), ((0, 0.008, -0.07), (0.026, 0.04, 0.008))],
               (0, 0.008, 0.04), STEEL),
    model_empty("Pistol_Muzzle", (0, -0.16, 0.065)),
    model_empty("Pistol_Eject", (0.016, -0.035, 0.075)),
]
WPN_PISTOL = tools.make_weapon_rig(PISTOL_PARTS, arm, attach)

# Rigged placeholder shotgun (Receiver, Pump, Trigger, Shell) - same tool, different weapon type
SHOTGUN_PARTS = [
    model_part("Shotgun_Receiver", [((0, -0.08, 0.06), (0.045, 0.26, 0.07)), ((0, -0.48, 0.08), (0.024, 0.55, 0.024)),
                                    ((0, -0.40, 0.045), (0.022, 0.40, 0.022)), ((0, 0.20, 0.03), (0.04, 0.30, 0.09)),
                                    ((0, 0.0, -0.01), (0.03, 0.04, 0.10))], (0, 0, 0), BROWN),
    model_part("Shotgun_Pump", [((0, -0.32, 0.045), (0.05, 0.16, 0.05))], (0, -0.32, 0.045), DARK),
    model_part("Shotgun_Trigger", [((0, -0.04, 0.015), (0.006, 0.008, 0.024))], (0, -0.038, 0.028), DARK),
    model_part("Shotgun_Shell", [((0, -0.06, 0.02), (0.02, 0.065, 0.02))], (0, -0.06, 0.02), (0.7, 0.1, 0.1, 1)),
    model_empty("Shotgun_Muzzle", (0, -0.755, 0.08)),
    model_empty("Shotgun_Eject", (0.025, -0.08, 0.07)),
]
WPN_SHOTGUN = tools.make_weapon_rig(SHOTGUN_PARTS, arm, attach)

REFS = {
    "Rifle": blocks("REF_Rifle", [
        ((0, 0.06, 0.10), (0.04, 0.07, 0.30)), ((0, 0.075, 0.42), (0.02, 0.02, 0.36)),
        ((0, 0.05, -0.17), (0.035, 0.08, 0.24)), ((0, -0.01, 0.0), (0.03, 0.10, 0.04)),
        ((0, 0.0, 0.08), (0.025, 0.09, 0.04)), ((0, 0.035, 0.26), (0.035, 0.045, 0.14))], ORANGE),
    "Bat": blocks("REF_Bat", [  # handle runs along the grip axis (socket Y)
        ((0, -0.11, 0), (0.05, 0.02, 0.05)), ((0, 0.05, 0), (0.03, 0.30, 0.03)),
        ((0, 0.40, 0), (0.05, 0.40, 0.05)), ((0, 0.62, 0), (0.065, 0.12, 0.065))], BROWN),
    "Crowbar": blocks("REF_Crowbar", [
        ((0, 0.25, 0), (0.02, 0.62, 0.02)), ((0, 0.57, 0.035), (0.02, 0.02, 0.07)),
        ((0, -0.07, 0.02), (0.02, 0.02, 0.05))], STEEL),
    "Key": blocks("REF_Key", [  # held between thumb and index; blade forward
        ((0, 0.0, 0.0), (0.004, 0.025, 0.025)), ((0, 0.0, 0.035), (0.003, 0.01, 0.045))], GOLD),
}


def show_ref(which=None):
    tools.apply_weapon(which or "")


# ---------------------------------------------------------------- final rest check
bpy.context.view_layer.update()
worst = max((pbs[n].matrix.to_quaternion().rotation_difference(arm.data.bones[n].matrix_local.to_quaternion()).angle,
             n) for n in DEFORM + ["AnimCamera"])
worst_loc = max(((pbs[n].matrix.translation - arm.data.bones[n].matrix_local.translation).length, n)
                for n in DEFORM + ["AnimCamera"])
# Blender pose matrices are float32: angles below ~0.04 deg read as 0 here.
print(f"rest check (float32, ~0.04 deg floor): max rotation error {math.degrees(worst[0]):.4f} deg ({worst[1]}), "
      f"max location error {worst_loc[0] * 1000:.3f} mm ({worst_loc[1]})")

# ---------------------------------------------------------------- start poses / test animation
# Built with the same keying + switch logic as the FPS Rig panel (fps_rig_tools.py).
FOLLOW_DEFAULTS = {"CTRL_Hand_IK.L": 1.0, "CTRL_Hand_IK.R": 1.0, "CTRL_Weapon": 1.0, "CTRL_Camera": 0.0}
CTRLS = [pb.name for pb in pbs if pb.name.startswith("CTRL_")]
MIRROR = Matrix.Diagonal((-1.0, 1.0, 1.0, 1.0))
HAND_IN_SOCKET_R = socket_in_hand.inverted()                 # right hand (bone frame) in socket space
HAND_IN_SOCKET_L = MIRROR @ HAND_IN_SOCKET_R @ MIRROR         # mirrored grip for the left hand
EYE_TARGET = EYE_WORLD + Vector((0, -10.0, 0))               # aim point 10 m ahead of the eyes


def upd():
    arm.update_tag()
    bpy.context.view_layer.update()


def set_world(name, pos, y=None, z=None):
    """Pose a control at a world position; optional local Y/Z toward world directions."""
    upd()
    pb = pbs[name]
    rot = (MW @ pb.matrix).to_3x3().normalized()
    if y is not None:
        rot = frame(y, z)
    pb.matrix = Matrix.LocRotScale(INV @ Vector(pos), (INV3 @ rot).normalized().to_quaternion(), Vector((1, 1, 1)))
    upd()


def set_world_matrix(name, world):
    upd()
    pbs[name].matrix = Matrix.LocRotScale(INV @ world.translation, (INV3 @ world.to_3x3()).normalized().to_quaternion(),
                                          Vector((1, 1, 1)))
    upd()


def world_of(name):
    upd()
    m = MW @ pbs[name].matrix
    return Matrix.LocRotScale(m.translation, m.to_quaternion(), Vector((1, 1, 1)))


def socket_frame(pos, barrel, up):
    """World matrix of the weapon socket: Y = weapon up, Z = barrel / business end."""
    return Matrix.Translation(Vector(pos)) @ frame(up, barrel).to_4x4()


def place_weapon(pos, barrel, up):
    set_world("CTRL_Weapon", pos, barrel, up)  # CTRL_Weapon: Y = barrel, Z = up


def right_hand_to_socket(sock):
    """Right hand placed so that the socket lands on `sock` (used while Follow Weapon = 0)."""
    set_world_matrix("CTRL_Hand_IK.R", sock @ HAND_IN_SOCKET_R)


def left_hand_on_socket(offset=(0, 0, 0), sock=None):
    """Left hand gripping the weapon, mirrored right-hand grip shifted by offset (socket space, m)."""
    sock = sock or world_of("WPN_Socket")
    set_world_matrix("CTRL_Hand_IK.L", sock @ Matrix.Translation(Vector(offset)) @ HAND_IN_SOCKET_L)


def fingers(side, grip=0, thumb=0, index=0, spread=0, thumb_spread=0):
    pbs[f"CTRL_Grip.{side}"].rotation_euler = (math.radians(grip), 0, math.radians(spread))
    pbs[f"CTRL_Thumb.{side}"].rotation_euler = (math.radians(thumb), 0, math.radians(thumb_spread))
    pbs[f"CTRL_Index.{side}"].rotation_euler = (math.radians(index), 0, 0)


def rot(name, x=0.0, y=0.0, z=0.0):
    pbs[name].rotation_euler = (math.radians(x), math.radians(y), math.radians(z))


def reset_pose(follow=None):
    for pb in pbs:
        pb.matrix_basis = Matrix()
    for name, value in {**FOLLOW_DEFAULTS, **(follow or {})}.items():
        pbs[name][tools.FOLLOW_PROPS[name]] = value
    upd()


def new_action(name, start, end):
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    arm.animation_data.action = act
    act.use_frame_range = True
    act.frame_start, act.frame_end = start, end
    return act


def key_all(f):
    for n in CTRLS:
        tools.key_control(arm, n, f)


def make_cyclic():
    for fc in tools.action_fcurves(arm):
        if not any(m.type == "CYCLES" for m in fc.modifiers):
            fc.modifiers.new("CYCLES")


def looping_action(name, follow, pose, keys):
    """Idle loop over frames 1-60: pose(phase) sets the full pose for phase 0..1; keys at the given frames."""
    new_action(name, 1, 60)
    for f in keys:
        scene.frame_set(f)
        reset_pose(follow)
        pose(((f - 1) % 60) / 60.0)
        key_all(f)
    make_cyclic()


def breath(phase, amount=1.0):
    """Breathing: chest lifts and opens slightly; 0 at phase 0, max at 0.5."""
    b = (1 - math.cos(2 * math.pi * phase)) / 2 * amount
    return b


arm.animation_data_create()
LOOP3 = (1, 31, 61)
LOOP5 = (1, 16, 31, 46, 61)


# Unarmed idle: arms relaxed, slight breathing
def unarmed_body(b):
    pbs["CTRL_Torso"].location = (0, -0.005 + 0.003 * b, 0)  # torso Y = up
    rot("CTRL_Chest", -1.2 * b)
    rot("CTRL_UpperChest", -0.8 * b)
    rot("CTRL_Neck", 2.0 + 0.6 * b)
    rot("CTRL_Shoulder.L", 4 - 0.8 * b)  # shoulder local +X lowers the shoulder on both sides
    rot("CTRL_Shoulder.R", 4 - 0.8 * b)


def unarmed_arms(b=0.0):
    set_world("CTRL_Elbow_Pole.L", (0.24, 0.45, 1.15))
    set_world("CTRL_Elbow_Pole.R", (-0.24, 0.45, 1.15))
    set_world("CTRL_Hand_IK.L", (0.215, 0.025, 0.935 + 0.003 * b), (0.08, -0.12, -1), (-1, 0.2, 0))
    set_world("CTRL_Hand_IK.R", (-0.215, 0.025, 0.935 + 0.003 * b), (-0.08, -0.12, -1), (1, 0.2, 0))
    fingers("L", 22, 12, -4)
    fingers("R", 22, 12, -4)


UNARMED = {"CTRL_Hand_IK.L": 0.0, "CTRL_Hand_IK.R": 0.0}


def unarmed_pose(phase):
    b = breath(phase)
    unarmed_body(b)
    unarmed_arms(b)


looping_action("Unarmed_Idle", UNARMED, unarmed_pose, LOOP3)


# Guard idle: fists up, light sway and breathing; fists ride with the chest
def guard_pose(phase):
    b = breath(phase)
    sway = math.sin(2 * math.pi * phase)
    pbs["CTRL_Torso"].location = (0.010 * sway, -0.03 + 0.004 * b, 0)
    rot("CTRL_Torso", 0, -12 + 2.0 * sway, 0)  # bladed stance, slight weave
    rot("CTRL_Chest", 5 - 1.2 * b)
    rot("CTRL_UpperChest", 4 - 0.8 * b, 2 * sway)
    rot("CTRL_Neck", -4)
    rot("CTRL_Head", -4, 10)
    set_world("CTRL_Elbow_Pole.L", (0.42, -0.10, 1.00))
    set_world("CTRL_Elbow_Pole.R", (-0.42, -0.10, 1.00))
    fingers("L", 88, 28)  # thumb across the front of the fist
    fingers("R", 88, 28)
    # fists defined relative to the upper chest, so they follow breathing/sway
    chest = world_of("CTRL_UpperChest")
    for side, pos, y, z in (("L", (0.14, -0.36, 1.38), (-0.10, -0.70, 0.70), (-0.90, 0.30, 0.0)),
                            ("R", (-0.15, -0.30, 1.35), (0.10, -0.70, 0.70), (0.90, 0.30, 0.0))):
        local = GUARD_CHEST_INV @ (Matrix.Translation(Vector(pos)) @ frame(y, z).to_4x4())
        set_world_matrix(f"CTRL_Hand_IK.{side}", chest @ local)


reset_pose(UNARMED)
pbs["CTRL_Torso"].location = (0, -0.03, 0)
rot("CTRL_Torso", 0, -12, 0)
rot("CTRL_Chest", 5)
rot("CTRL_UpperChest", 4)
GUARD_CHEST_INV = world_of("CTRL_UpperChest").inverted()
looping_action("Guard_Idle", UNARMED, guard_pose, LOOP5)


# Melee: bat (two hands, left follows the weapon) and crowbar (right hand only)
def melee_body(b, lean=4):
    pbs["CTRL_Torso"].location = (0, -0.02 + 0.003 * b, 0)
    rot("CTRL_Chest", lean - 1.2 * b)
    rot("CTRL_UpperChest", 2 - 0.8 * b)


def bat_pose(phase):
    melee_body(breath(phase))
    place_weapon((-0.17, -0.20, 1.27), (0, -1, 0.2), (-0.20, 0.45, 0.87))
    left_hand_on_socket((0.0, -0.10, 0.0))
    set_world("CTRL_Elbow_Pole.R", (-0.50, 0.10, 1.05))
    set_world("CTRL_Elbow_Pole.L", (0.30, -0.30, 0.90))
    fingers("R", 82, 55, thumb_spread=-60)  # thumb wrapped around the handle
    fingers("L", 82, 55, thumb_spread=-60)


looping_action("Melee_Bat_Idle", {}, bat_pose, LOOP3)


def crowbar_pose(phase):
    b = breath(phase)
    melee_body(b, lean=3)
    place_weapon((-0.20, -0.26, 1.10), (0, -1, -0.3), (0.10, -0.35, 0.93))
    set_world("CTRL_Hand_IK.L", (0.22, -0.10, 1.00 + 0.003 * b), (0.05, -0.45, -0.89), (-1, 0.2, 0))
    set_world("CTRL_Elbow_Pole.R", (-0.45, 0.10, 0.95))
    set_world("CTRL_Elbow_Pole.L", (0.30, 0.40, 1.10))
    fingers("R", 80, -20, thumb_spread=25)  # thumb along the bar
    fingers("L", 40, 20)


looping_action("Melee_Crowbar_Idle", {"CTRL_Hand_IK.L": 0.0}, crowbar_pose, LOOP3)

# Pistol at the hip, two hands, barrel on the screen centre 10 m ahead
PISTOL_HIP = Vector((-0.10, -0.42, 1.46))
PISTOL_AIM = (EYE_TARGET - PISTOL_HIP).normalized()
PISTOL_SUPPORT = (-0.015, -0.025, 0.0)  # left-hand grip offset from the mirrored right grip (socket space)


def pistol_fingers():
    fingers("R", 70, 50, -40, thumb_spread=-50)  # thumb wrapped along the left side of the frame
    fingers("L", 78, 30)


def pistol_hip_pose(phase):
    b = breath(phase)
    melee_body(b, lean=3)
    place_weapon(PISTOL_HIP, PISTOL_AIM, (0, 0, 1))
    left_hand_on_socket(PISTOL_SUPPORT)
    set_world("CTRL_Elbow_Pole.R", (-0.40, 0.00, 0.95))
    set_world("CTRL_Elbow_Pole.L", (0.40, -0.10, 0.95))
    pistol_fingers()


looping_action("Pistol_Idle_Hip", {}, pistol_hip_pose, LOOP3)

# Pistol_Draw (test animation): unarmed idle -> hand to holster -> pistol appears -> hip aim
act = new_action("Pistol_Draw", 1, 24)
act.pose_markers.new("WeaponShow").frame = 8
DRAW_FOLLOW = {"CTRL_Hand_IK.L": 0.0, "CTRL_Hand_IK.R": 0.0}
HOLSTER = socket_frame((-0.215, 0.04, 0.97), (0, 0.05, -1), (0, -1, 0))
DRAW_UP = socket_frame((-0.20, -0.02, 1.12), (0, -0.55, -0.8), (0, -0.8, 0.55))
DRAW_FWD = socket_frame((-0.12, -0.30, 1.25), (0, -1, 0.05), (0, 0, 1))
DRAW_AIM = socket_frame(PISTOL_HIP, PISTOL_AIM, (0, 0, 1))
right_keys = {8: HOLSTER, 12: DRAW_UP, 16: DRAW_FWD, 20: DRAW_AIM, 24: DRAW_AIM}
for f in (1, 4, 8, 12, 16, 20, 24):
    scene.frame_set(f)
    reset_pose(DRAW_FOLLOW)
    if f <= 4:
        unarmed_body(0.0)
        unarmed_arms()
        if f == 4:  # anticipation: right hand starts moving back to the hip
            set_world("CTRL_Hand_IK.R", (-0.225, 0.06, 0.97), (-0.1, -0.2, -1), (1, 0.2, 0))
            fingers("R", 10, 5)
    else:
        melee_body(0.0, lean=3 if f >= 16 else 1)
        set_world("CTRL_Elbow_Pole.R", (-0.45, 0.25 if f < 16 else 0.0, 1.0 if f < 16 else 0.95))
        right_hand_to_socket(right_keys[f])
        fingers("R", 70, 50, -40 if f >= 12 else 0, thumb_spread=-50)
        if f < 16:  # left hand still relaxed, starting to come up
            set_world("CTRL_Elbow_Pole.L", (0.24, 0.45, 1.15))
            set_world("CTRL_Hand_IK.L", (0.20, -0.03 - 0.02 * (f >= 12), 0.96 + 0.06 * (f >= 12)),
                      (0.0, -0.4, -0.9), (-1, 0.2, 0))
            fingers("L", 22, 12)
    key_all(f)
# left hand reaches the pistol at f16: place it on the grip (world), then switch to Follow Weapon = 1
scene.frame_set(16)
set_world("CTRL_Elbow_Pole.L", (0.40, -0.10, 0.95))
left_hand_on_socket(PISTOL_SUPPORT)
pistol_fingers()
for n in ("CTRL_Hand_IK.L", "CTRL_Elbow_Pole.L", "CTRL_Grip.L", "CTRL_Thumb.L", "CTRL_Index.L"):
    tools.key_control(arm, n, 16)
tools.switch_follow(arm, "CTRL_Hand_IK.L", 1.0, frame=16)
local_l = pbs["CTRL_Hand_IK.L"].matrix_basis.copy()  # grip relative to the weapon from now on
for f in (20, 24):
    scene.frame_set(f)
    pbs["CTRL_Hand_IK.L"]["Follow Weapon"] = 1.0  # overrides the 0 keyed in the first pass
    pbs["CTRL_Hand_IK.L"].matrix_basis = local_l
    set_world("CTRL_Elbow_Pole.L", (0.40, -0.10, 0.95))
    pistol_fingers()
    for n in ("CTRL_Hand_IK.L", "CTRL_Elbow_Pole.L", "CTRL_Grip.L", "CTRL_Thumb.L", "CTRL_Index.L"):
        tools.key_control(arm, n, f)
scene.frame_set(24)
print("draw end: left hand on pistol error %.4f m" % (
    (world_of("CTRL_Hand_IK.L").translation - (world_of("WPN_Socket") @ Matrix.Translation(Vector(PISTOL_SUPPORT))
                                                @ HAND_IN_SOCKET_L).translation).length))

# ---------------------------------------------------------------- weapon animation examples (Pistol)
# Character + pistol parts in ONE Action: the pistol rig gets its own slot (tools.ensure_weapon_action).
W_CTRLS = ("CTRL_Root", "CTRL_Slide", "CTRL_Trigger", "CTRL_Magazine")


def wpb(n):
    return WPN_PISTOL.pose.bones[n]


def wreset():
    for n in W_CTRLS:
        wpb(n).matrix_basis = Matrix()
    wpb("CTRL_Magazine")["Follow Left Hand"] = 0.0
    WPN_PISTOL.update_tag()


def wkey(f, names=W_CTRLS):
    for n in names:
        tools.key_control(WPN_PISTOL, n, f)


def tilt(aim, up, deg):
    """Rotate barrel + up direction upward (around the weapon's lateral axis)."""
    r = Matrix.Rotation(math.radians(deg), 3, aim.cross(up).normalized())
    return (r @ aim).normalized(), (r @ up).normalized()


def pistol_root_world():
    upd()
    return WPN_PISTOL.matrix_world @ WPN_PISTOL.pose.bones["Pistol_Root"].matrix  # modelling frame -> world


def set_weapon_ctrl_world(name, world):
    WPN_PISTOL.update_tag()  # re-evaluate drivers after a slider change
    upd()
    m = WPN_PISTOL.matrix_world.inverted() @ world
    wpb(name).matrix = Matrix.LocRotScale(m.translation, m.to_quaternion(), Vector((1, 1, 1)))
    upd()


# Pistol_Draw: the pistol is hidden (CTRL_Root scale 0) until it is drawn from the holster at f8
act = bpy.data.actions["Pistol_Draw"]
arm.animation_data.action = act
tools.ensure_weapon_action(WPN_PISTOL, act)
for f, shown in ((1, 0.0), (7, 0.0), (8, 1.0), (24, 1.0)):
    scene.frame_set(f)
    wreset()
    wpb("CTRL_Root").scale = (shown,) * 3
    wkey(f)

# Pistol_Fire: hip shot - trigger, slide cycle, recoil in the hands, small camera kick
act = new_action("Pistol_Fire", 1, 12)
tools.set_action_weapon(act, "Pistol")
act.pose_markers.new("Fire").frame = 2
FIRE = {1: (0, 0, 0, 0), 2: (1.0, 1.0, 0.75, 0.6), 3: (1.0, 1.0, 1.0, 1.0), 4: (0.0, 0.5, 0.7, 0.7),
        5: (0.0, 0.0, 0.35, 0.4), 6: (0.0, 0.0, -0.08, 0.15), 8: (0.0, 0.0, 0.03, 0.05),
        12: (0, 0, 0, 0)}  # slide, trigger, kick (negative = settle overshoot), camera (0..1)
for f, (sl, tr, kick, cam) in FIRE.items():
    scene.frame_set(f)
    reset_pose()
    wreset()
    melee_body(0.0, lean=3)
    rot("CTRL_UpperChest", 2 - 2.0 * kick)  # the shot pushes the upper body back a little
    rot("CTRL_Head", -1.0 * kick)
    aim, up = tilt(PISTOL_AIM, Vector((0, 0, 1)), 17 * kick)  # muzzle flip
    place_weapon(PISTOL_HIP - PISTOL_AIM * 0.05 * kick + Vector((0, 0, 0.018 * kick)), aim, up)
    left_hand_on_socket(PISTOL_SUPPORT)
    set_world("CTRL_Elbow_Pole.R", (-0.40, 0.00, 0.95))
    set_world("CTRL_Elbow_Pole.L", (0.40, -0.10, 0.95))
    pistol_fingers()
    rot("CTRL_Camera", -1.5 * cam)  # camera control: -X pitches up
    wpb("CTRL_Slide").location = (0, 0.026 * sl, 0)  # slide back along the barrel axis
    wpb("CTRL_Trigger").rotation_euler = (math.radians(22 * tr), 0, 0)
    key_all(f)
    wkey(f)

# Pistol_Reload: magazine out, new magazine from the left hip, inserted, back to two-handed grip
act = new_action("Pistol_Reload", 1, 52)
tools.set_action_weapon(act, "Pistol")
for name, frame_ in (("MagOut", 8), ("MagDrop", 12), ("MagShow", 22), ("MagIn", 34)):
    act.pose_markers.new(name).frame = frame_
R_POS = Vector((-0.07, -0.33, 1.34))
R_AIM = Vector((0.18, -0.9, 0.40)).normalized()
R_UP = Vector((0.45, 0.05, 0.9))
MAG_REST = Matrix.Translation((0, 0.008, 0.04))                       # magazine pivot (modelling frame)
_yh = Vector((-0.3, -0.95, 0.05)).normalized()
_zh = Vector((0, 0, 1))
_base = Vector((0, 0.008, -0.074))                                     # magazine base plate
HAND_INSERT = Matrix.Translation(_base - _yh * 0.06 - _zh * 0.03) @ frame(_yh, _zh).to_4x4()  # palm under the mag
MAG_IN_HAND = HAND_INSERT.inverted() @ MAG_REST                        # magazine relative to the left hand
for f in (1, 6, 8, 12, 20, 22, 26, 30, 34, 38, 44, 48, 52):
    scene.frame_set(f)
    reset_pose()
    wreset()
    melee_body(0.0, lean=3 if f in (1, 48, 52) else 5)
    if f in (1, 48, 52):
        place_weapon(PISTOL_HIP, PISTOL_AIM, (0, 0, 1))
    else:
        place_weapon(R_POS, R_AIM, R_UP)
    set_world("CTRL_Elbow_Pole.R", (-0.40, 0.00, 0.95))
    set_world("CTRL_Elbow_Pole.L", (0.40, -0.10, 0.95))
    left_hand_on_socket(PISTOL_SUPPORT)  # overridden below where the left hand is free
    pistol_fingers()
    if f == 8:
        fingers("R", 70, 40, -40, thumb_spread=-35)  # thumb presses the magazine release
    key_all(f)
    wkey(f)
# left hand lets go at f8 and works in world space until it is back on the grip at f44
tools.switch_follow(arm, "CTRL_Hand_IK.L", 0.0, frame=8)
LEFT_FREE = {
    12: ((0.17, -0.15, 1.10), (0.0, -0.4, -0.9), (-1, 0.1, 0), (30, 15)),  # straight down toward the pouch
    20: ((0.215, -0.02, 1.02), (0.0, -0.25, -1), (-1, 0.1, 0), (60, 35)),  # magazine pouch, left hip
    22: ((0.20, -0.06, 1.06), (-0.1, -0.5, -0.85), (-1, 0.1, 0), (60, 35)),  # leaving the pouch with the new mag
    26: ((0.08, -0.28, 1.20), (-0.3, -0.9, 0.3), (0, 0, 1), (60, 35)),
}
for f in (12, 20, 22, 26, 30, 34, 38):
    scene.frame_set(f)
    pbs["CTRL_Hand_IK.L"]["Follow Weapon"] = 0.0
    set_world("CTRL_Elbow_Pole.L", (0.30, 0.20, 1.00))
    if f in LEFT_FREE:
        pos, y, z, (g, t) = LEFT_FREE[f]
        set_world("CTRL_Hand_IK.L", pos, y, z)
    else:  # f30: magazine 6 cm below the grip, f34/f38: pushed in
        below = Matrix.Translation((0, 0, -0.06)) if f == 30 else Matrix()
        set_world_matrix("CTRL_Hand_IK.L", pistol_root_world() @ below @ HAND_INSERT)
        g, t = 60, 35
    fingers("L", g, t)
    for n in ("CTRL_Hand_IK.L", "CTRL_Elbow_Pole.L", "CTRL_Grip.L", "CTRL_Thumb.L", "CTRL_Index.L"):
        tools.key_control(arm, n, f)
# back on the grip at f44 (placed in world space first), then Follow Weapon = 1 without a jump
scene.frame_set(44)
pbs["CTRL_Hand_IK.L"]["Follow Weapon"] = 0.0
set_world("CTRL_Elbow_Pole.L", (0.40, -0.10, 0.95))
left_hand_on_socket(PISTOL_SUPPORT)
pistol_fingers()
for n in ("CTRL_Hand_IK.L", "CTRL_Elbow_Pole.L", "CTRL_Grip.L", "CTRL_Thumb.L", "CTRL_Index.L"):
    tools.key_control(arm, n, 44)
tools.switch_follow(arm, "CTRL_Hand_IK.L", 1.0, frame=44)
for f in (48, 52):
    scene.frame_set(f)
    pbs["CTRL_Hand_IK.L"]["Follow Weapon"] = 1.0
    left_hand_on_socket(PISTOL_SUPPORT)
    tools.key_control(arm, "CTRL_Hand_IK.L", f)
# magazine: slides out (f8-12), falls (f12-16), hidden (scale 0, f17-21), appears in the left hand (f22),
# inserted (f34). In Unity the MagDrop event can instead hide it and spawn a physics magazine at f12.
for f, out in ((10, 0.05), (12, 0.13)):
    scene.frame_set(f)
    wpb("CTRL_Magazine")["Follow Left Hand"] = 0.0
    wpb("CTRL_Magazine").matrix_basis = Matrix.Translation((0, 0, -out))
    wkey(f, ("CTRL_Magazine",))
scene.frame_set(12)
mag12 = (WPN_PISTOL.matrix_world @ wpb("CTRL_Magazine").matrix).copy()
for f, drop, tumble in ((14, 0.22, 20), (16, 0.80, 65)):  # gravity: world down, accelerating, tumbling
    scene.frame_set(f)
    wpb("CTRL_Magazine")["Follow Left Hand"] = 0.0
    m = Matrix.Translation((0, 0, -drop)) @ mag12 @ Matrix.Rotation(math.radians(tumble), 4, "X")
    set_weapon_ctrl_world("CTRL_Magazine", Matrix.LocRotScale(m.translation, m.to_quaternion(), Vector((1, 1, 1))))
    wkey(f, ("CTRL_Magazine",))
fallen = wpb("CTRL_Magazine").matrix_basis.copy()
for f in (17, 20, 21):
    scene.frame_set(f)
    wpb("CTRL_Magazine")["Follow Left Hand"] = 0.0
    wpb("CTRL_Magazine").matrix_basis = fallen
    wpb("CTRL_Magazine").scale = (0.0, 0.0, 0.0)
    wkey(f, ("CTRL_Magazine",))
scene.frame_set(22)
wpb("CTRL_Magazine")["Follow Left Hand"] = 1.0
set_weapon_ctrl_world("CTRL_Magazine", world_of(P + "LeftHand") @ MAG_IN_HAND)
mag_in_hand = wpb("CTRL_Magazine").matrix_basis.copy()
wkey(22, ("CTRL_Magazine",))
for f in (26, 30, 34):
    scene.frame_set(f)
    wpb("CTRL_Magazine")["Follow Left Hand"] = 1.0
    wpb("CTRL_Magazine").matrix_basis = mag_in_hand
    wkey(f, ("CTRL_Magazine",))
tools.switch_follow(WPN_PISTOL, "CTRL_Magazine", 0.0, frame=34)  # seated: back in the weapon, no jump
scene.frame_set(34)
print("reload: magazine seated offset %.4f m" % wpb("CTRL_Magazine").matrix_basis.translation.length)

# Example_FPS_Ready: rifle ready pose (kept from v1)
new_action("Example_FPS_Ready", 1, 30)
for f in (1, 30):
    scene.frame_set(f)
    reset_pose()
    rot("CTRL_Chest", 0, -8)
    rot("CTRL_UpperChest", 0, -10)
    rot("CTRL_Shoulder.L", 0, 0, 12)
    grip = Vector((-0.11, -0.30, 1.47))
    place_weapon(grip, FWD, UP)  # right hand holds the weapon via the socket offset
    yl = Vector((-0.8, -0.5, 0.15)).normalized()
    zl = Vector((0, 0, 1)); zl = (zl - zl.project(yl)).normalized()
    set_world("CTRL_Hand_IK.L", grip + Vector((0, -0.19, 0)) - yl * 0.06 - zl * 0.035, yl, zl)
    set_world("CTRL_Elbow_Pole.R", (-0.55, 0.0, 0.95))
    set_world("CTRL_Elbow_Pole.L", (0.45, -0.25, 0.85))
    fingers("R", 65, 30, -45, thumb_spread=-10)
    fingers("L", 45, -10, thumb_spread=-10)
    key_all(f)

# Which weapon each Action uses (the FPS Rig panel shows it and shares the Action with a rigged weapon)
for name, w in {"Unarmed_Idle": "", "Guard_Idle": "", "Melee_Bat_Idle": "Bat", "Melee_Crowbar_Idle": "Crowbar",
                "Pistol_Idle_Hip": "Pistol", "Pistol_Draw": "Pistol", "Pistol_Fire": "Pistol",
                "Pistol_Reload": "Pistol", "Example_FPS_Ready": "Rifle"}.items():
    bpy.data.actions[name]["Weapon"] = w

# Open on the neutral idle, no weapon shown
arm.animation_data.action = bpy.data.actions["Unarmed_Idle"]
scene.frame_start, scene.frame_end = 1, 60
scene.frame_set(1)
tools.apply_weapon("", arm.animation_data.action)

# FPS_View sits inside the head: hide back faces so the inside of the head is not drawn
for mat in mesh_obj.data.materials:
    if mat:
        mat.use_backface_culling = True
for screen in bpy.data.screens:
    for area in screen.areas:
        for space in area.spaces:
            if space.type == "VIEW_3D":
                space.shading.show_backface_culling = True
scene.display.shading.show_backface_culling = True

# "Animation" tab: the small 3D view looks through the FPS camera, the Dope Sheet is the Action Editor
anim_screen = bpy.data.screens.get("Animation")
if anim_screen:
    views = [a for a in anim_screen.areas if a.type == "VIEW_3D"]
    if len(views) > 1:
        small = min(views, key=lambda a: a.width * a.height)
        small.spaces[0].region_3d.view_perspective = "CAMERA"
    for area in anim_screen.areas:
        if area.type == "DOPESHEET_EDITOR":
            area.spaces[0].ui_mode = "ACTION"

# Embed the FPS Rig panel (registers itself when the file is opened)
t = bpy.data.texts.new("fps_rig_tools.py")
t.from_string(open(TOOLS_SCRIPT).read())
t.use_module = True

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
