"""FPS Rig tools: an "FPS Rig" tab in the 3D View sidebar (N panel).

- Action: Start/End (the timeline follows), Fit to keys, Match End to Start, Select control groups.
- Switch Follow (keep pose): flip a control's Follow slider without the control jumping.
- Weapon for this Action: which weapon an Action uses (shown automatically, shares the Action).
- Make / Update Weapon Rig: build a small rig for a weapon from its separate part objects.
- Export this Action / Export all Actions: character clip (+ weapon clip) per Action.
- Export Weapon Model: the weapon's model + skeleton for a Unity prefab.
- FPS Rig – Tutorial: step-by-step practice for a body and a weapon animation.

Embedded in Blender/FPS_Rig.blend as a text block that registers itself when the file is
opened (if Blender blocks scripts: click "Allow Execution", or open the text and Run Script).
The rig works without this panel; see Docs/ANIMATOR_GUIDE.md for the manual alternatives.
"""
import math
import os
import re

import bpy
from bpy.app.handlers import persistent
from bpy_extras import anim_utils
from mathutils import Matrix, Vector

ARMATURE = "Armature"
# character control -> its space-switch slider
FOLLOW_PROPS = {
    "CTRL_Hand_IK.L": "Follow Weapon",
    "CTRL_Hand_IK.R": "Follow Weapon",
    "CTRL_Weapon": "Follow Chest",
    "CTRL_Camera": "Follow Head",
}
WEAPONS_COLLECTION = "Weapons"
LEFT_HAND_PROP = "PROP_Hand.L"          # character bone: left-hand prop socket
RX90 = Matrix.Rotation(math.radians(90.0), 4, "X")  # weapon armature: local Y up / Z barrel, like the socket

# Weapon parts: motion type from the part name (case-insensitive, first match wins)
MOTION_RULES = [
    ("charginghandle", "SLIDE"), ("boltcarrier", "SLIDE"), ("bolthandle", "ROTATE"),
    ("magazine", "DETACH"), ("mag", "DETACH"), ("shell", "DETACH"), ("clip", "DETACH"),
    ("grenade", "DETACH"), ("round", "DETACH"), ("ammo", "DETACH"),
    ("trigger", "ROTATE"), ("hammer", "ROTATE"), ("safety", "ROTATE"), ("selector", "ROTATE"),
    ("lever", "ROTATE"), ("cylinder", "ROTATE"), ("hinge", "ROTATE"), ("break", "ROTATE"),
    ("stock", "ROTATE"), ("sight", "ROTATE"), ("latch", "ROTATE"), ("release", "ROTATE"),
    ("slide", "SLIDE"), ("bolt", "SLIDE"), ("pump", "SLIDE"), ("forend", "SLIDE"),
    ("carrier", "SLIDE"), ("charging", "SLIDE"),
]
BODY_NAMES = ("frame", "body", "receiver")
EFFECT_NAMES = ("muzzle", "eject")
MOTION_COLORS = {"SLIDE": "THEME02", "ROTATE": "THEME09", "DETACH": "THEME03", "FREE": "THEME07", "ROOT": "THEME10"}
MOTION_ITEMS = [("SLIDE", "Slide", "Moves along one axis (slide, bolt, pump)"),
                ("ROTATE", "Rotate", "Rotates around one axis (trigger, hammer, selector)"),
                ("DETACH", "Detachable", "Free, can follow the left hand (magazine, shell)"),
                ("FREE", "Free", "No locks")]
AXIS_ITEMS = [("X", "X", ""), ("Y", "Y", ""), ("Z", "Z", "")]


# ---------------------------------------------------------------- generic helpers
def get_rig():
    return bpy.data.objects.get(ARMATURE)


def upd():
    bpy.context.view_layer.update()


def action_fcurves(obj):
    """F-curves of the object's active Action slot (Blender 4.4+ slotted actions)."""
    ad = obj.animation_data
    if not ad or not ad.action or not ad.action_slot:
        return []
    cb = anim_utils.action_get_channelbag_for_slot(ad.action, ad.action_slot)
    return cb.fcurves if cb else []


def follow_prop(pb):
    """Name of the Follow slider on a control (character or weapon rig), or None."""
    if pb.id_data.name == ARMATURE and pb.name in FOLLOW_PROPS:
        return FOLLOW_PROPS[pb.name]
    for k in pb.keys():
        if k.startswith("Follow "):
            return k
    return None


def key_control(obj, name, frame):
    """Key location, rotation and (if any) the Follow slider of one control."""
    pb = obj.pose.bones[name]
    pb.keyframe_insert("location", frame=frame)
    pb.keyframe_insert("rotation_quaternion" if pb.rotation_mode == "QUATERNION" else "rotation_euler", frame=frame)
    if str(pb.get("Motion", "")).split(" ")[0] in ("DETACH", "ROOT"):
        pb.keyframe_insert("scale", frame=frame)  # scale 0 = hidden (also in Unity)
        path = f'pose.bones["{name}"].scale'
        for fc in action_fcurves(obj):
            if fc.data_path == path:
                for kp in fc.keyframe_points:
                    kp.interpolation = "CONSTANT"  # show/hide snaps, never shrinks
    prop = follow_prop(pb)
    if prop:
        pb.keyframe_insert(f'["{prop}"]', frame=frame)
        path = f'pose.bones["{name}"]["{prop}"]'
        for fc in action_fcurves(obj):
            if fc.data_path == path:
                for kp in fc.keyframe_points:
                    kp.interpolation = "CONSTANT"  # sliders switch, never blend


def switch_follow(obj, name, value=None, frame=None, key=True):
    """Set a Follow slider (toggle if value is None) keeping the control's world transform.

    With key=True: the old slider + transform are held on frame-1 and the new ones keyed on frame.
    """
    scene = bpy.context.scene
    pb = obj.pose.bones[name]
    prop = follow_prop(pb)
    frame = scene.frame_current if frame is None else frame
    if value is None:
        value = 0.0 if pb[prop] >= 0.5 else 1.0
    animated = key and obj.animation_data and obj.animation_data.action
    if animated:
        scene.frame_set(frame - 1)
        key_control(obj, name, frame - 1)
    scene.frame_set(frame)
    world = obj.matrix_world @ pb.matrix
    pb[prop] = value
    obj.update_tag()
    upd()
    pb.matrix = obj.matrix_world.inverted() @ world
    upd()
    if key:
        key_control(obj, name, frame)
    return value


def _clean(name):
    return re.sub(r"\.\d+$", "", name)


def _exports_dir(*sub):
    base = bpy.path.abspath("//") or os.getcwd()
    d = os.path.normpath(os.path.join(base, "..", "Exports", *sub))
    os.makedirs(d, exist_ok=True)
    return d


# ---------------------------------------------------------------- weapons: collections / sync
def weapon_names():
    col = bpy.data.collections.get(WEAPONS_COLLECTION)
    if not col:
        return []
    return [re.sub(r"^(WPN|REF)_", "", c.name) for c in col.children]


def weapon_collection(name):
    col = bpy.data.collections.get(WEAPONS_COLLECTION)
    if not col:
        return None
    for c in col.children:
        if re.sub(r"^(WPN|REF)_", "", c.name) == name:
            return c
    return None


def _layer_collection(view_layer, col):
    def walk(lc):
        if lc.collection == col:
            return lc
        for ch in lc.children:
            r = walk(ch)
            if r:
                return r
        return None
    return walk(view_layer.layer_collection)


def weapon_rig(name):
    obj = bpy.data.objects.get("WPN_" + name) if name else None
    return obj if obj and obj.type == "ARMATURE" else None


def reset_weapon_pose(wobj):
    for pb in wobj.pose.bones:
        pb.matrix_basis = Matrix()  # also scale 1: visible
        prop = follow_prop(pb)
        if prop:
            pb[prop] = 0.0
    wobj.update_tag()


def ensure_weapon_action(wobj, act):
    """Give the weapon rig the same Action as the character, in its own slot (created if missing)."""
    ad = wobj.animation_data_create()
    slot = next((s for s in act.slots if s.name_display == wobj.name), None)
    if ad.action != act:
        reset_weapon_pose(wobj)  # channels this clip does not key go back to rest
        ad.action = act
    if slot is None:
        slot = act.slots.new(id_type="OBJECT", name=wobj.name)
    if ad.action_slot != slot:
        ad.action_slot = slot
    return slot


def apply_weapon(name, act=None, view_layer=None):
    """Show only the given weapon's collection; share the Action with its rig."""
    vl = view_layer or bpy.context.view_layer
    col = bpy.data.collections.get(WEAPONS_COLLECTION)
    if col:
        for c in col.children:
            lc = _layer_collection(vl, c)
            show = re.sub(r"^(WPN|REF)_", "", c.name) == name
            if lc and lc.hide_viewport == show:
                lc.hide_viewport = not show
            c.hide_render = not show
    wobj = weapon_rig(name)
    if wobj and act:
        ensure_weapon_action(wobj, act)


_sync_state = {"key": None, "paused": 0}


@persistent
def weapon_sync_handler(scene, depsgraph=None):
    if _sync_state["paused"]:
        return  # an export is temporarily showing a weapon
    arm = bpy.data.objects.get(ARMATURE)
    act = arm.animation_data.action if arm and arm.animation_data else None
    name = act.get("Weapon", "") if act else ""
    rng = tuple(int(round(f)) for f in act.frame_range) if act else None
    key = (act.name if act else "", name, rng)
    if key == _sync_state["key"]:
        return
    _sync_state["key"] = key
    try:
        apply_weapon(name, act)
        # the timeline follows the Action's frame range (only when the Action or its range changes)
        sc = bpy.context.scene
        if rng and (sc.frame_start, sc.frame_end) != rng:
            sc.frame_start, sc.frame_end = rng
    except Exception as e:  # never break the UI from a handler
        print("FPS Rig weapon sync:", e)


def set_action_weapon(act, name):
    act["Weapon"] = name
    _sync_state["key"] = None
    apply_weapon(name, act)


# ---------------------------------------------------------------- weapons: rig builder
def motion_of(suffix):
    s = suffix.lower()
    for kw, motion in MOTION_RULES:
        if kw in s:
            return motion
    return "FREE"


def classify_parts(objs):
    """-> weapon name, body object, moving parts, effect empties."""
    names = {o: _clean(o.name) for o in objs}
    body = next((o for o in objs if names[o].split("_", 1)[-1].lower() in BODY_NAMES), None)
    if body is None:
        raise RuntimeError("No main part found: name it <Weapon>_Frame, <Weapon>_Body or <Weapon>_Receiver.")
    wname = names[body].split("_", 1)[0]
    parts, effects = [], []
    for o in objs:
        if o is body:
            continue
        if not names[o].startswith(wname + "_"):
            raise RuntimeError(f"'{o.name}' does not start with '{wname}_' (all parts must be named <Weapon>_<Part>).")
        suffix = names[o][len(wname) + 1:]
        (effects if suffix.lower() in EFFECT_NAMES else parts).append(o)
    return wname, body, parts, effects


def set_motion(pb, motion, axis=None):
    """Lock a weapon control to its motion type (visible/editable as normal locks in the N panel)."""
    axis = axis or ("Y" if motion == "SLIDE" else "X")
    i = "XYZ".index(axis)
    pb.rotation_mode = "XYZ"
    pb.lock_scale = (motion != "DETACH",) * 3  # detachable parts: scale 0 hides them
    if motion == "ROOT":  # whole weapon: only scale (0 = hidden, 1 = shown)
        pb.lock_location = pb.lock_rotation = (True, True, True)
        pb.lock_scale = (False, False, False)
    elif motion == "SLIDE":
        pb.lock_location = tuple(k != i for k in range(3))
        pb.lock_rotation = (True, True, True)
    elif motion == "ROTATE":
        pb.lock_location = (True, True, True)
        pb.lock_rotation = tuple(k != i for k in range(3))
    else:
        pb.lock_location = (False, False, False)
        pb.lock_rotation = (False, False, False)
    pb["Motion"] = f"{motion} {axis}" if motion in ("SLIDE", "ROTATE") else motion
    pb.color.palette = MOTION_COLORS[motion]
    pb.bone.color.palette = MOTION_COLORS[motion]


def _box_widget(name, corners, margin=0.004):
    mn = Vector((min(c[i] for c in corners) - margin for i in range(3)))
    mx = Vector((max(c[i] for c in corners) + margin for i in range(3)))
    vs = [(x, y, z) for x in (mn.x, mx.x) for y in (mn.y, mx.y) for z in (mn.z, mx.z)]
    es = [(0, 1), (2, 3), (4, 5), (6, 7), (0, 2), (1, 3), (4, 6), (5, 7), (0, 4), (1, 5), (2, 6), (3, 7)]
    me = bpy.data.meshes.get(name) or bpy.data.meshes.new(name)
    me.clear_geometry()
    me.from_pydata(vs, es, [])
    ob = bpy.data.objects.get(name)
    if ob is None:
        ob = bpy.data.objects.new(name, me)
        wcol = bpy.data.collections.get("Widgets")
        if wcol is None:
            wcol = bpy.data.collections.new("Widgets")
            bpy.context.scene.collection.children.link(wcol)
            wcol.hide_viewport = wcol.hide_render = True
        wcol.objects.link(ob)
    return ob


def make_weapon_rig(objs, character=None, attach=None):
    """Create or update WPN_<Weapon> from part objects modelled at the origin (grip), barrel -Y, up +Z.

    Bones are placed at each part's pivot (object origin) with the pivot's axes relative to the main
    part; object hierarchy among parts becomes bone hierarchy. Animation is kept on update (bone
    names = part names). Returns the weapon armature object.
    """
    character = character or bpy.data.objects.get(ARMATURE)
    attach = attach or bpy.data.objects.get("WPN_Attach")
    scene = bpy.context.scene
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    wname, body, parts, effects = classify_parts(objs)
    all_objs = [body] + parts + effects
    clean = {o: _clean(o.name) for o in all_objs}
    suffix = {o: clean[o][len(wname) + 1:] for o in parts + effects}

    # collection Weapons/WPN_<name>
    root_col = bpy.data.collections.get(WEAPONS_COLLECTION)
    if root_col is None:
        root_col = bpy.data.collections.new(WEAPONS_COLLECTION)
        scene.collection.children.link(root_col)
    col = bpy.data.collections.get("WPN_" + wname)
    if col is None:
        col = bpy.data.collections.new("WPN_" + wname)
        root_col.children.link(col)

    # weapon armature, detached to the modelling frame while (re)building
    wobj = bpy.data.objects.get("WPN_" + wname)
    if wobj is None:
        wobj = bpy.data.objects.new("WPN_" + wname, bpy.data.armatures.new("WPN_" + wname))
        col.objects.link(wobj)
        wobj.show_in_front = True
        wobj.data.display_type = "OCTAHEDRAL"
    wobj.parent = None
    wobj.matrix_world = RX90.copy()
    wobj.data.pose_position = "REST"

    # world matrices of the parts; bake object scale into mesh data (Max/FBX imports are often 0.01)
    upd()  # newly created/imported objects only get a valid matrix_world after an update
    W = {o: o.matrix_world.copy() for o in all_objs}
    body_rot = W[body].to_quaternion()

    def size_of(o):
        if o.type != "MESH" or not o.data.vertices:
            return 0.03
        s = o.matrix_world.to_scale()
        cs = [Vector(c) for c in o.bound_box]
        return max((max(c[i] for c in cs) - min(c[i] for c in cs)) * s[i] for i in range(3))

    sizes = {o: size_of(o) for o in all_objs}
    for o in all_objs:
        s = W[o].to_scale()
        if o.type == "MESH" and (s - Vector((1, 1, 1))).length > 1e-6:
            if o.data.users > 1:
                o.data = o.data.copy()
            o.data.transform(Matrix.Diagonal(s).to_4x4())

    def pivot(o):  # pivot in the modelling frame; axes relative to the main part
        return Matrix.LocRotScale(W[o].translation, body_rot.inverted() @ W[o].to_quaternion(), Vector((1, 1, 1)))

    def part_parent(o):  # nearest ancestor that is itself a moving part
        p = o.parent
        while p is not None and p not in parts:
            p = p.parent
        return p

    # replace objects left over from a previous import of the same parts
    for o in all_objs:
        old = bpy.data.objects.get(clean[o])
        if old is not None and old is not o and old.parent == wobj:
            bpy.data.objects.remove(old)

    root_name = f"{wname}_Root"
    bone_of = {body: root_name}
    for o in parts + effects:
        bone_of[o] = clean[o]

    lc = _layer_collection(bpy.context.view_layer, col)
    if lc:
        lc.hide_viewport = False  # must be visible to edit
    for o in bpy.context.selected_objects:
        o.select_set(False)
    wobj.hide_set(False)
    wobj.select_set(True)
    bpy.context.view_layer.objects.active = wobj
    bpy.ops.object.mode_set(mode="EDIT")
    eb = wobj.data.edit_bones
    inv = wobj.matrix_world.inverted()

    def put(name, world, parent, deform, length):
        b = eb.get(name) or eb.new(name)
        b.length = max(0.015, min(length, 0.08))
        m = inv @ world
        b.matrix = Matrix.LocRotScale(m.translation, m.to_quaternion(), Vector((1, 1, 1)))
        b.parent = eb.get(parent) if parent else None
        b.use_deform = deform
        return b

    put(root_name, Matrix(), None, True, 0.05)
    put("CTRL_Root", Matrix(), None, False, 0.05)  # whole weapon: scale 0 hides it
    for o in parts:
        pp = part_parent(o)
        L = sizes[o] * 0.5
        put(bone_of[o], pivot(o), bone_of[pp] if pp else root_name, True, L)
        ctrl_parent = ("CTRL_" + suffix[pp]) if pp else root_name
        if motion_of(suffix[o]) == "DETACH":
            put("MCH_Space_" + suffix[o], pivot(o), root_name, False, L)
            ctrl_parent = "MCH_Space_" + suffix[o]
        put("CTRL_" + suffix[o], pivot(o), ctrl_parent, False, L)
    for o in effects:
        pp = part_parent(o)
        put(bone_of[o], pivot(o), bone_of[pp] if pp else root_name, True, 0.02)
    bpy.ops.object.mode_set(mode="OBJECT")

    # bone collections
    bcols = wobj.data.collections
    c_ctrl = bcols.get("Controls") or bcols.new("Controls")
    c_def = bcols.get("Deform") or bcols.new("Deform")
    c_mch = bcols.get("Mechanism") or bcols.new("Mechanism")
    c_def.is_visible = c_mch.is_visible = False

    pbs = wobj.pose.bones
    c_def.assign(wobj.data.bones[root_name])
    c_ctrl.assign(wobj.data.bones["CTRL_Root"])
    root_pb = pbs[root_name]
    for c in list(root_pb.constraints):
        root_pb.constraints.remove(c)
    con = root_pb.constraints.new("COPY_TRANSFORMS")
    con.target, con.subtarget = wobj, "CTRL_Root"
    set_motion(pbs["CTRL_Root"], "ROOT")
    if body.type == "MESH" and body.data.vertices:
        bone_world = wobj.matrix_world @ wobj.data.bones["CTRL_Root"].matrix_local
        to_bone = bone_world.inverted() @ Matrix.LocRotScale(W[body].translation, W[body].to_quaternion(), Vector((1, 1, 1)))
        pbs["CTRL_Root"].custom_shape = _box_widget(f"WGT_{wname}_Root", [to_bone @ Vector(v.co) for v in body.data.vertices],
                                                    margin=0.012)
        pbs["CTRL_Root"].use_custom_shape_bone_size = False
    for o in effects:
        c_def.assign(wobj.data.bones[bone_of[o]])
    for o in parts:
        sfx, motion = suffix[o], motion_of(suffix[o])
        deform, ctrl = pbs[bone_of[o]], pbs["CTRL_" + sfx]
        c_def.assign(deform.bone)
        c_ctrl.assign(ctrl.bone)
        for c in list(deform.constraints):
            deform.constraints.remove(c)
        con = deform.constraints.new("COPY_TRANSFORMS")
        con.target, con.subtarget = wobj, ctrl.name
        if "Motion" not in ctrl:  # keep a type chosen earlier in the panel
            set_motion(ctrl, motion)
        if motion == "DETACH":
            ctrl["Follow Left Hand"] = ctrl.get("Follow Left Hand", 0.0)
            ctrl.id_properties_ui("Follow Left Hand").update(
                min=0.0, max=1.0, default=0.0, description="0 = stays in the weapon, 1 = held in the left hand")
            mch = pbs["MCH_Space_" + sfx]
            c_mch.assign(mch.bone)
            for c in list(mch.constraints):
                mch.constraints.remove(c)
            if character and LEFT_HAND_PROP in character.pose.bones:
                con = mch.constraints.new("COPY_TRANSFORMS")
                con.name = "Follow Left Hand"
                con.target, con.subtarget = character, LEFT_HAND_PROP
                path = f'pose.bones["{mch.name}"].constraints["Follow Left Hand"].influence'
                wobj.driver_remove(path)
                d = wobj.driver_add(path).driver
                d.type = "AVERAGE"
                v = d.variables.new()
                v.type = "SINGLE_PROP"
                v.targets[0].id_type = "OBJECT"
                v.targets[0].id = wobj
                v.targets[0].data_path = f'pose.bones["{ctrl.name}"]["Follow Left Hand"]'
        # control shape: a wire box around the part, in bone space
        if o.type == "MESH" and o.data.vertices:
            bone_world = wobj.matrix_world @ wobj.data.bones[ctrl.name].matrix_local
            to_bone = bone_world.inverted() @ Matrix.LocRotScale(W[o].translation, W[o].to_quaternion(), Vector((1, 1, 1)))
            corners = [to_bone @ Vector(v.co) for v in o.data.vertices]
            ctrl.custom_shape = _box_widget(f"WGT_{wname}_{sfx}", corners)
            ctrl.use_custom_shape_bone_size = False
            ctrl.custom_shape_wire_width = 2.0

    # parent the parts rigidly to their bones (at rest), clean names, one collection
    upd()
    for o in all_objs:
        o.parent = wobj
        o.parent_type = "BONE"
        o.parent_bone = bone_of[o]
        upd()
        o.matrix_world = Matrix.LocRotScale(W[o].translation, W[o].to_quaternion(), Vector((1, 1, 1)))
        o.name = clean[o]
        for c in list(o.users_collection):
            c.objects.unlink(o)
        col.objects.link(o)
        o.hide_select = True
        if o.type == "EMPTY":
            o.empty_display_size = 0.02

    wobj.data.pose_position = "POSE"
    if attach is not None:
        wobj.parent = attach
        wobj.matrix_parent_inverse = Matrix()
        wobj.matrix_basis = Matrix()
    upd()
    return wobj


# ---------------------------------------------------------------- export
def _fbx(filepath, object_types, bake, deform_only=True):
    bpy.ops.export_scene.fbx(
        filepath=filepath,
        use_selection=True,
        object_types=object_types,
        apply_scale_options="FBX_SCALE_UNITS",  # rigs are in metres with scale 1
        axis_forward="-Z",
        axis_up="Y",
        bake_space_transform=False,
        use_armature_deform_only=deform_only,
        add_leaf_bones=False,
        primary_bone_axis="Y",
        secondary_bone_axis="X",
        armature_nodetype="NULL",
        bake_anim=bake,
        bake_anim_use_all_bones=True,
        bake_anim_use_nla_strips=False,
        bake_anim_use_all_actions=False,
        bake_anim_force_startend_keying=True,
        bake_anim_step=1.0,
        bake_anim_simplify_factor=0.0,
    )


class _ExportState:
    """Save/restore mode, selection, frame range and scene name around an export."""

    def __init__(self, start=None, end=None, take=None):
        self.start, self.end, self.take = start, end, take

    def __enter__(self):
        sc = bpy.context.scene
        self.obj = bpy.context.object
        self.mode = self.obj.mode if self.obj else "OBJECT"
        if self.obj and self.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        self.prev = (sc.frame_start, sc.frame_end, sc.frame_current, sc.name,
                     list(bpy.context.selected_objects), bpy.context.view_layer.objects.active)
        if self.start is not None:
            sc.frame_start, sc.frame_end = self.start, self.end
        if self.take:
            sc.name = self.take  # single-take FBX exports are named after the scene
        for o in bpy.context.selected_objects:
            o.select_set(False)
        return self

    def __exit__(self, *exc):
        sc = bpy.context.scene
        sc.frame_start, sc.frame_end, sc.name = self.prev[0], self.prev[1], self.prev[3]
        sc.frame_set(self.prev[2])
        for o in bpy.context.selected_objects:
            o.select_set(False)
        for o in self.prev[4]:
            if o.name in bpy.data.objects:
                o.select_set(True)
        bpy.context.view_layer.objects.active = self.prev[5]
        if self.obj and self.mode != "OBJECT" and bpy.context.view_layer.objects.active == self.obj:
            bpy.ops.object.mode_set(mode=self.mode)
        return False


class _Visible:
    """Temporarily show a weapon's collection (hidden objects are not evaluated or selectable)."""

    def __init__(self, wobj):
        self.cols = list(wobj.users_collection)

    def __enter__(self):
        _sync_state["paused"] += 1
        vl = bpy.context.view_layer
        self.lcs = [(lc, lc.hide_viewport) for lc in (_layer_collection(vl, c) for c in self.cols) if lc]
        for lc, _ in self.lcs:
            lc.hide_viewport = False
        upd()
        return self

    def __exit__(self, *exc):
        for lc, h in self.lcs:
            lc.hide_viewport = h
        _sync_state["paused"] -= 1
        return False


def export_weapon_action(act, wobj, filepath=None):
    """Weapon clip: the weapon's deform bones relative to its root, baked from the rig (incl. a
    magazine following the hand), on a temporary unconstrained copy at the origin."""
    start, end = (int(round(f)) for f in act.frame_range)
    wname = wobj.name[4:] if wobj.name.startswith("WPN_") else wobj.name
    if filepath is None:
        filepath = os.path.join(_exports_dir("Weapons", wname), f"{wobj.name}@{bpy.path.clean_name(act.name)}.fbx")
    scene = bpy.context.scene
    ensure_weapon_action(wobj, act)
    with _Visible(wobj):
        return _export_weapon_action(act, wobj, filepath, start, end, scene)


def _export_weapon_action(act, wobj, filepath, start, end, scene):
    deform = [b for b in wobj.data.bones if b.use_deform]
    order = sorted(deform, key=lambda b: len(b.parent_recursive))
    frames = {}
    for f in range(start, end + 1):
        scene.frame_set(f)
        loc = {}
        for b in order:
            pb = wobj.pose.bones[b.name]
            # inverted_safe: a hidden (scale 0) parent has no proper inverse
            loc[b.name] = (pb.parent.matrix.inverted_safe() @ pb.matrix) if pb.parent else pb.matrix.copy()
        frames[f] = loc
    name = wobj.name
    wobj.name = name + "__src"
    tmp = bpy.data.objects.new(name, wobj.data)
    scene.collection.objects.link(tmp)
    tmp.matrix_world = RX90.copy()
    upd()  # a new object only gets its pose after an update
    tact = bpy.data.actions.new("__weapon_export")
    tmp.animation_data_create().action = tact
    try:
        for f, loc in frames.items():
            for b in order:
                rest_rel = (b.parent.matrix_local.inverted() @ b.matrix_local) if b.parent else b.matrix_local
                pb = tmp.pose.bones[b.name]
                pb.rotation_mode = "QUATERNION"
                pb.matrix_basis = rest_rel.inverted() @ loc[b.name]
                for path in ("location", "rotation_quaternion", "scale"):
                    pb.keyframe_insert(path, frame=f)
        with _ExportState(start, end, act.name):
            tmp.select_set(True)
            bpy.context.view_layer.objects.active = tmp
            _fbx(filepath, {"ARMATURE"}, bake=True)
    finally:
        bpy.data.objects.remove(tmp)
        bpy.data.actions.remove(tact)
        wobj.name = name
    print(f"Exported weapon clip '{act.name}' -> {filepath}")
    return filepath


def export_weapon_model(wobj, filepath=None):
    """Weapon model + skeleton at rest, root at the grip: +Z barrel, +Y up in Unity."""
    wname = wobj.name[4:] if wobj.name.startswith("WPN_") else wobj.name
    if filepath is None:
        filepath = os.path.join(_exports_dir("Weapons", wname), f"{wobj.name}.fbx")
    prev = (wobj.parent, wobj.matrix_parent_inverse.copy(), wobj.matrix_basis.copy(), wobj.data.pose_position)
    meshes = [o for o in wobj.children if o.type == "MESH"]
    vis = _Visible(wobj).__enter__()
    hidden = {o: o.hide_get() for o in [wobj] + meshes}
    try:
        wobj.parent = None
        wobj.matrix_world = RX90.copy()
        wobj.data.pose_position = "REST"
        upd()
        with _ExportState():
            for o in [wobj] + meshes:
                o.hide_set(False)
                o.hide_select = False
                o.select_set(True)
            bpy.context.view_layer.objects.active = wobj
            _fbx(filepath, {"ARMATURE", "MESH"}, bake=False)
    finally:
        wobj.parent = prev[0]
        wobj.matrix_parent_inverse = prev[1]
        wobj.matrix_basis = prev[2]
        wobj.data.pose_position = prev[3]
        for o, h in hidden.items():
            o.hide_set(h)
            o.hide_select = o is not wobj
        vis.__exit__()
        upd()
    print(f"Exported weapon model -> {filepath}")
    return filepath


def export_choices():
    """(character, weapon) export toggles from the FPS Rig panel (both on by default)."""
    sc = bpy.context.scene
    return getattr(sc, "fpsrig_export_character", True), getattr(sc, "fpsrig_export_weapon", True)


def export_active_action(filepath=None):
    """Character clip to Exports/<Action>.fbx and/or the weapon clip, per the panel's Body/Weapon toggles."""
    arm = get_rig()
    act = arm.animation_data.action if arm.animation_data else None
    if act is None:
        raise RuntimeError("The rig has no active Action. Assign one in the Action Editor first.")
    do_char, do_weapon = export_choices()
    wobj = weapon_rig(act.get("Weapon", "")) if do_weapon else None
    if not do_char and not do_weapon:
        raise RuntimeError("Nothing to export: tick Body and/or Weapon in the FPS Rig panel.")
    if not do_char and wobj is None:
        raise RuntimeError(f"'{act.name}' has no rigged weapon (Weapon for this Action), and Body is off.")
    start, end = (int(round(f)) for f in act.frame_range)
    result = None
    if do_char:
        if filepath is None:
            filepath = os.path.join(_exports_dir(), bpy.path.clean_name(act.name) + ".fbx")
        with _ExportState(start, end, act.name):
            arm.select_set(True)
            bpy.context.view_layer.objects.active = arm
            _fbx(filepath, {"ARMATURE"}, bake=True)
        print(f"Exported '{act.name}' frames {start}-{end} -> {filepath}")
        result = filepath
    if wobj is not None:
        wpath = export_weapon_action(act, wobj)
        result = result or wpath
    return result


def rig_actions(arm):
    """Actions made for this rig (they animate the character's CTRL_ bones)."""
    out = []
    for act in bpy.data.actions:
        for slot in act.slots:
            if slot.name_display.startswith("WPN_"):
                continue
            cb = anim_utils.action_get_channelbag_for_slot(act, slot)
            if cb and any(fc.data_path.startswith('pose.bones["CTRL_') for fc in cb.fcurves):
                out.append((act, slot))
                break
    return out


def export_all_actions():
    arm = get_rig()
    ad = arm.animation_data_create()
    prev = (ad.action, ad.action_slot)
    paths = []
    try:
        for act, slot in rig_actions(arm):
            ad.action = act
            ad.action_slot = slot
            try:
                paths.append(export_active_action())
            except RuntimeError as e:  # e.g. Body off and this Action has no rigged weapon
                print(f"Skipped '{act.name}': {e}")
    finally:
        ad.action = prev[0]
        if prev[0]:
            ad.action_slot = prev[1]
        _sync_state["key"] = None
    return paths


# ---------------------------------------------------------------- timeline / selection / match end
def _active_action():
    arm = get_rig()
    return arm.animation_data.action if arm and arm.animation_data else None


def action_key_range(act):
    """First and last keyframe over all slots (character and weapon)."""
    frames = []
    for slot in act.slots:
        cb = anim_utils.action_get_channelbag_for_slot(act, slot)
        if cb:
            for fc in cb.fcurves:
                frames += [kp.co[0] for kp in fc.keyframe_points]
    return (min(frames), max(frames)) if frames else (None, None)


def fit_range_to_keys(act):
    lo, hi = action_key_range(act)
    if lo is None:
        return False
    act.use_frame_range = True
    act.frame_start, act.frame_end = int(round(lo)), int(round(max(hi, lo + 1)))
    return True


FINGER_PREFIXES = ("CTRL_Grip", "CTRL_Thumb", "CTRL_Index", "CTRL_Middle", "CTRL_Ring", "CTRL_Pinky")
GROUP_ITEMS = [("ALL", "All", "All controls of the character and the weapon"),
               ("BODY", "Body", "Character controls except fingers"),
               ("FINGERS", "Fingers", "Finger controls (both hands)"),
               ("WEAPON", "Weapon", "CTRL_Weapon and the weapon's part controls")]


def _shown(pb):
    cols = pb.bone.collections
    return not cols or any(c.is_visible for c in cols)


def rigs():
    """(character, weapon rig of the active Action or None)."""
    act = _active_action()
    return get_rig(), (weapon_rig(act.get("Weapon", "")) if act else None)


def control_group(group, visible_only=True):
    arm, wobj = rigs()
    ok = (lambda pb: _shown(pb)) if visible_only else (lambda pb: True)
    char = [(arm, pb) for pb in arm.pose.bones if pb.name.startswith("CTRL_") and ok(pb)]
    weap = [(wobj, pb) for pb in wobj.pose.bones if pb.name.startswith("CTRL_") and ok(pb)] if wobj else []
    fingers = [(o, pb) for o, pb in char if pb.name.startswith(FINGER_PREFIXES)]
    if group == "ALL":
        return char + weap
    if group == "BODY":
        return [(o, pb) for o, pb in char if not pb.name.startswith(FINGER_PREFIXES)]
    if group == "FINGERS":
        return fingers
    return [(o, pb) for o, pb in char if pb.name == "CTRL_Weapon"] + weap


def enter_pose_mode():
    """Character + the Action's weapon rig together in Pose Mode (multi-object)."""
    arm, wobj = rigs()
    objs = [arm] + ([wobj] if wobj else [])
    if all(o.mode == "POSE" for o in objs) and bpy.context.object in objs:
        return objs
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    for o in bpy.context.selected_objects:
        o.select_set(False)
    for o in objs:
        o.hide_set(False)
        o.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="POSE")
    return objs


def _set_select(pb, state):
    if hasattr(pb, "select"):
        pb.select = state
    else:
        pb.bone.select = state


def _is_selected(pb):
    return pb.select if hasattr(pb, "select") else pb.bone.select


def select_controls(group):
    objs = enter_pose_mode()
    for o in objs:
        for pb in o.pose.bones:
            _set_select(pb, False)
    chosen = control_group(group)
    for o, pb in chosen:
        _set_select(pb, True)
    if chosen:
        o, pb = chosen[0]
        o.data.bones.active = pb.bone
    return chosen


def select_bone(obj, name):
    objs = enter_pose_mode()
    for o in objs:
        for pb in o.pose.bones:
            _set_select(pb, False)
    pb = obj.pose.bones[name]
    _set_select(pb, True)
    obj.data.bones.active = pb.bone
    bpy.context.view_layer.objects.active = obj


def match_end_to_start(only_selected=True):
    """Copy the pose of the Action's first frame to its last frame and key it (selected controls, or all)."""
    act = _active_action()
    if act is None:
        raise RuntimeError("No active Action.")
    arm, wobj = rigs()
    if wobj:
        ensure_weapon_action(wobj, act)
    every = control_group("ALL", visible_only=False)
    chosen = [(o, pb) for o, pb in every if _is_selected(pb)] if only_selected else []
    chosen = chosen or every
    sc = bpy.context.scene
    start, end = (int(round(f)) for f in act.frame_range)
    sc.frame_set(start)
    saved = {}
    for o, pb in chosen:
        prop = follow_prop(pb)
        saved[(o.name, pb.name)] = (pb.matrix_basis.copy(), pb[prop] if prop else None)
    sc.frame_set(end)
    for o, pb in chosen:
        basis, value = saved[(o.name, pb.name)]
        pb.matrix_basis = basis
        prop = follow_prop(pb)
        if prop:
            pb[prop] = value
    for o in {o for o, _ in chosen}:
        o.update_tag()
    upd()
    for o, pb in chosen:
        key_control(o, pb.name, end)
    return len(chosen)


# ---------------------------------------------------------------- interactive tutorial
def _export_path(*parts):
    base = bpy.path.abspath("//") or os.getcwd()
    return os.path.normpath(os.path.join(base, "..", "Exports", *parts))


def _fc(obj, bone, prop, index):
    path = f'pose.bones["{bone}"].{prop}'
    for fc in action_fcurves(obj):
        if fc.data_path == path and fc.array_index == index:
            return fc
    return None


def _has_key(obj, bone, frame, prop="location"):
    for fc in action_fcurves(obj):
        if fc.data_path.startswith(f'pose.bones["{bone}"].{prop}') and any(abs(k.co[0] - frame) < 0.5 for k in fc.keyframe_points):
            return True
    return False


def _value(obj, bone, prop, index, frame):
    fc = _fc(obj, bone, prop, index)
    return fc.evaluate(frame) if fc else None


def _quat_at(obj, bone, frame):
    from mathutils import Quaternion
    vals = [_value(obj, bone, "rotation_quaternion", i, frame) for i in range(4)]
    return None if None in vals else Quaternion(vals)


TUT = {
    "BODY": {"action": "Tut_Crouch", "source": "Unarmed_Idle", "range": (1, 30), "weapon": ""},
    "WEAPON": {"action": "Tut_PistolCheck", "source": "Pistol_Idle_Hip", "range": (1, 40), "weapon": "M1911"},
}


def tut_action_ok(kind):
    act = _active_action()
    return act is not None and act.name == TUT[kind]["action"]


def tut_new_action(kind):
    """Fresh tutorial Action: a copy of the start pose with only its first-frame keys, no loop."""
    cfg = TUT[kind]
    old = bpy.data.actions.get(cfg["action"])
    if old:
        bpy.data.actions.remove(old)
    act = bpy.data.actions[cfg["source"]].copy()
    act.name = cfg["action"]
    start, end = cfg["range"]
    for slot in act.slots:
        cb = anim_utils.action_get_channelbag_for_slot(act, slot)
        if not cb:
            continue
        for fc in cb.fcurves:
            for m in list(fc.modifiers):
                fc.modifiers.remove(m)  # no loop
            for kp in reversed(list(fc.keyframe_points)):
                if kp.co[0] > start + 0.5:
                    fc.keyframe_points.remove(kp)  # keep just the start pose
    act.use_fake_user = True
    act.use_frame_range = True
    act.frame_start, act.frame_end = start, end
    act["Weapon"] = cfg["weapon"]
    arm = get_rig()
    ad = arm.animation_data_create()
    ad.action = act
    ad.action_slot = next(s for s in act.slots if not s.name_display.startswith("WPN_"))
    _sync_state["key"] = None
    apply_weapon(cfg["weapon"], act)
    bpy.context.scene.frame_set(start)
    return act


def _tut_ensure(kind):
    if not tut_action_ok(kind):
        tut_new_action(kind)


def _go(frame):
    bpy.context.scene.frame_set(frame)


# --- body tutorial: crouch and stand up
def _b_crouch_do():
    _tut_ensure("BODY")
    _go(15)
    arm = get_rig()
    select_bone(arm, "CTRL_Torso")
    arm.pose.bones["CTRL_Torso"].location = (0, -0.30, 0)
    key_control(arm, "CTRL_Torso", 15)


def _b_crouch_check():
    v = _value(get_rig(), "CTRL_Torso", "location", 1, 15)
    return tut_action_ok("BODY") and _has_key(get_rig(), "CTRL_Torso", 15) and v is not None and v < -0.12


def _b_head_do():
    _tut_ensure("BODY")
    _go(15)
    arm = get_rig()
    select_bone(arm, "CTRL_Head")
    arm.pose.bones["CTRL_Head"].rotation_euler = (math.radians(15), 0, 0)
    key_control(arm, "CTRL_Head", 15)


def _b_head_check():
    v = _value(get_rig(), "CTRL_Head", "rotation_euler", 0, 15)
    return tut_action_ok("BODY") and _has_key(get_rig(), "CTRL_Head", 15, "rotation") and v is not None and abs(v) > math.radians(5)


def _match_do(kind):
    def do():
        _tut_ensure(kind)
        enter_pose_mode()
        match_end_to_start(only_selected=False)
    return do


def _match_check(kind, bone, prop, index):
    def check():
        if not tut_action_ok(kind):
            return False
        end = TUT[kind]["range"][1]
        a, b = _value(get_rig(), bone, prop, index, 1), _value(get_rig(), bone, prop, index, end)
        return _has_key(get_rig(), bone, end, prop.split("_")[0]) and a is not None and b is not None and abs(a - b) < 1e-4
    return check


def _export_do(kind):
    def do():
        _tut_ensure(kind)
        sc = bpy.context.scene
        if hasattr(sc, "fpsrig_export_character"):
            sc.fpsrig_export_character = True
            sc.fpsrig_export_weapon = True
        export_active_action()
    return do


def _w_select_do():
    _tut_ensure("WEAPON")
    select_controls("WEAPON")


def _w_select_check():
    arm, wobj = rigs()
    return tut_action_ok("WEAPON") and wobj is not None and arm.mode == "POSE" and wobj.mode == "POSE"


def _w_lift_do():
    _tut_ensure("WEAPON")
    _go(12)
    arm = get_rig()
    select_bone(arm, "CTRL_Weapon")
    pb = arm.pose.bones["CTRL_Weapon"]
    m = pb.matrix.copy()
    lift = arm.matrix_world.inverted().to_3x3() @ Vector((0, 0, 0.05))
    m = Matrix.Translation(lift) @ m @ Matrix.Rotation(math.radians(35), 4, "Z") @ Matrix.Rotation(math.radians(20), 4, "X")
    pb.matrix = Matrix.LocRotScale(m.translation, m.to_quaternion(), Vector((1, 1, 1)))
    upd()
    key_control(arm, "CTRL_Weapon", 12)


def _w_lift_check():
    a, b = _quat_at(get_rig(), "CTRL_Weapon", 1), _quat_at(get_rig(), "CTRL_Weapon", 12)
    return (tut_action_ok("WEAPON") and _has_key(get_rig(), "CTRL_Weapon", 12, "rotation") and a is not None and b is not None
            and math.degrees(a.rotation_difference(b).angle) > 10)


def _w_hold_do():
    _tut_ensure("WEAPON")
    _go(30)
    arm = get_rig()
    select_bone(arm, "CTRL_Weapon")
    key_control(arm, "CTRL_Weapon", 30)


def _w_hold_check():
    a, b = _quat_at(get_rig(), "CTRL_Weapon", 12), _quat_at(get_rig(), "CTRL_Weapon", 30)
    return (tut_action_ok("WEAPON") and _has_key(get_rig(), "CTRL_Weapon", 30, "rotation") and a is not None and b is not None
            and math.degrees(a.rotation_difference(b).angle) < 1)


def _w_slide_prepare():
    _tut_ensure("WEAPON")
    wobj = rigs()[1]
    _go(17)
    select_bone(wobj, "CTRL_Slide")
    wobj.pose.bones["CTRL_Slide"].location = (0, 0, 0)
    key_control(wobj, "CTRL_Slide", 17)  # slide at rest just before it is pulled
    _go(20)


def _w_slide_do():
    _w_slide_prepare()
    wobj = rigs()[1]
    wobj.pose.bones["CTRL_Slide"].location = (0, 0.025, 0)
    key_control(wobj, "CTRL_Slide", 20)


def _w_slide_check():
    wobj = rigs()[1]
    v = _value(wobj, "CTRL_Slide", "location", 1, 20) if wobj else None
    return tut_action_ok("WEAPON") and v is not None and v > 0.01 and _has_key(wobj, "CTRL_Slide", 20)


def _w_slide_fwd_prepare():
    _tut_ensure("WEAPON")
    _go(24)
    select_bone(rigs()[1], "CTRL_Slide")


def _w_slide_fwd_do():
    _w_slide_fwd_prepare()
    wobj = rigs()[1]
    wobj.pose.bones["CTRL_Slide"].location = (0, 0, 0)
    key_control(wobj, "CTRL_Slide", 24)


def _w_slide_fwd_check():
    wobj = rigs()[1]
    v = _value(wobj, "CTRL_Slide", "location", 1, 24) if wobj else None
    return tut_action_ok("WEAPON") and v is not None and abs(v) < 0.003 and _has_key(wobj, "CTRL_Slide", 24)


def _always():
    return True


TUTORIALS = {
    "BODY": [
        {"title": "Velkommen", "text": [
            "Du lager en enkel kroppsanimasjon:",
            "figuren går ned i huk og opp igjen.",
            "Hvert steg: les teksten, gjør det selv,",
            "og se etter den grønne haken.",
            "Står du fast: trykk «Vis meg».",
            "Trykk «Neste» for å starte."], "check": _always},
        {"title": "1. Ny animasjon", "text": [
            "Hver animasjon er en Action.",
            "Trykk «Vis meg» for å lage Tut_Crouch",
            "(kopi av Unarmed_Idle, 30 frames).",
            "Til vanlig: Action Editor → duplikat-",
            "knappen ved navnet, gi nytt navn."],
         "do": lambda: tut_new_action("BODY"), "check": lambda: tut_action_ok("BODY")},
        {"title": "2. Ned i huk (frame 15)", "text": [
            "Trykk «Gjør klart»: går til frame 15",
            "og velger CTRL_Torso (boksen ved hofta).",
            "Hold musa i 3D-vinduet:",
            "G, Z, skriv -0.3, Enter  (30 cm ned).",
            "Trykk I for å sette en nøkkel.",
            "Se: føttene blir stående, knærne bøyes."],
         "prepare": lambda: (_tut_ensure("BODY"), _go(15), select_bone(get_rig(), "CTRL_Torso")),
         "do": _b_crouch_do, "check": _b_crouch_check},
        {"title": "3. Se litt ned (frame 15)", "text": [
            "«Gjør klart» velger CTRL_Head.",
            "R, X, skriv 15, Enter  (hodet ned).",
            "Trykk I for å sette en nøkkel."],
         "prepare": lambda: (_tut_ensure("BODY"), _go(15), select_bone(get_rig(), "CTRL_Head")),
         "do": _b_head_do, "check": _b_head_check},
        {"title": "4. Tilbake til start (frame 30)", "text": [
            "Klippet skal slutte slik det startet.",
            "Velg bort alt (Alt+A i 3D-vinduet),",
            "og trykk «Match End to Start» i",
            "FPS Rig-panelet over: posen fra",
            "frame 1 kopieres til frame 30."],
         "prepare": lambda: (_tut_ensure("BODY"), _go(30)),
         "do": _match_do("BODY"), "check": _match_check("BODY", "CTRL_Torso", "location", 1)},
        {"title": "5. Se resultatet", "text": [
            "Space spiller av (Space igjen stopper).",
            "Numpad 0 = gjennom FPS-kameraet,",
            "Numpad 0 igjen = tilbake.",
            "Vil du endre noe: flytt til en frame,",
            "endre posen og trykk I igjen."],
         "prepare": lambda: _go(1), "check": _always},
        {"title": "6. Eksporter til Unity", "text": [
            "Trykk «Export this Action» (FPS Rig).",
            "Filen havner i Exports/Tut_Crouch.fbx.",
            "I Unity: Humanoid + Copy From Other",
            "Avatar, som med Mixamo-klipp."],
         "do": _export_do("BODY"), "check": lambda: os.path.exists(_export_path("Tut_Crouch.fbx"))},
        {"title": "Ferdig!", "text": [
            "Du har laget, finpusset og eksportert",
            "en animasjon. Neste: prøv",
            "Våpen-tutorialen i menyen over.",
            "«Start på nytt» sletter øvingsklippet."], "check": _always},
    ],
    "WEAPON": [
        {"title": "Velkommen", "text": [
            "Du animerer kropp og våpen sammen:",
            "løft pistolen, trekk sliden bak og",
            "fram, og tilbake til hofteposisjon.",
            "Begge havner i samme Action.",
            "Trykk «Neste» for å starte."], "check": _always},
        {"title": "1. Ny animasjon", "text": [
            "«Vis meg» lager Tut_PistolCheck",
            "(kopi av Pistol_Idle_Hip, 40 frames).",
            "Pistolen vises automatisk, fordi",
            "Actionen bruker våpenet «M1911»."],
         "do": lambda: tut_new_action("WEAPON"),
         "check": lambda: tut_action_ok("WEAPON") and _active_action().get("Weapon") == "M1911"},
        {"title": "2. Velg begge riggene", "text": [
            "Trykk «Select: Weapon» i FPS Rig.",
            "Da er figuren og pistolen i Pose Mode",
            "samtidig, og du kan ta tak i",
            "kontrollene på begge."],
         "do": _w_select_do, "check": _w_select_check},
        {"title": "3. Løft pistolen (frame 12)", "text": [
            "«Gjør klart» velger CTRL_Weapon",
            "(den oransje boksen langs løpet).",
            "R, Z, 35, Enter (vri inn mot deg),",
            "R, X, 20, Enter (vipp), G, Z, 0.05.",
            "Trykk I. Hendene følger med."],
         "prepare": lambda: (_tut_ensure("WEAPON"), _go(12), select_bone(get_rig(), "CTRL_Weapon")),
         "do": _w_lift_do, "check": _w_lift_check},
        {"title": "4. Hold posen (frame 30)", "text": [
            "«Gjør klart» går til frame 30.",
            "Trykk bare I (ikke flytt noe):",
            "pistolen holder posen fra 12 til 30."],
         "prepare": lambda: (_tut_ensure("WEAPON"), _go(30), select_bone(get_rig(), "CTRL_Weapon")),
         "do": _w_hold_do, "check": _w_hold_check},
        {"title": "5. Slide bak (frame 20)", "text": [
            "«Gjør klart» nøkler sliden i ro på",
            "frame 17, går til 20 og velger",
            "CTRL_Slide. Sett Location Y = 0.025",
            "i N → Item (eller G og dra: sliden",
            "kan bare gli langs løpet). Trykk I."],
         "prepare": _w_slide_prepare, "do": _w_slide_do, "check": _w_slide_check},
        {"title": "6. Slide fram (frame 24)", "text": [
            "«Gjør klart» går til frame 24.",
            "Alt+G nullstiller sliden. Trykk I."],
         "prepare": _w_slide_fwd_prepare, "do": _w_slide_fwd_do, "check": _w_slide_fwd_check},
        {"title": "7. Tilbake til start (frame 40)", "text": [
            "Velg bort alt (Alt+A) og trykk",
            "«Match End to Start»: kropp OG",
            "pistol får startposen på frame 40."],
         "prepare": lambda: (_tut_ensure("WEAPON"), _go(40)),
         "do": _match_do("WEAPON"), "check": _match_check("WEAPON", "CTRL_Weapon", "rotation_quaternion", 0)},
        {"title": "8. Se resultatet", "text": [
            "Space spiller av, Numpad 0 viser",
            "FPS-kameraet. Velg gjerne en frame",
            "og juster pose – trykk I igjen."],
         "prepare": lambda: _go(1), "check": _always},
        {"title": "9. Eksporter", "text": [
            "Kryss av Body og Weapon, og trykk",
            "«Export this Action». Du får:",
            " Exports/Tut_PistolCheck.fbx (kropp)",
            " Exports/Weapons/M1911/",
            "   WPN_M1911@Tut_PistolCheck.fbx"],
         "do": _export_do("WEAPON"),
         "check": lambda: os.path.exists(_export_path("Tut_PistolCheck.fbx")) and os.path.exists(
             _export_path("Weapons", "M1911", "WPN_M1911@Tut_PistolCheck.fbx"))},
        {"title": "Ferdig!", "text": [
            "Kropp og våpen er animert i samme",
            "Action og eksportert hver for seg.",
            "Se Docs/ANIMATOR_GUIDE.md for",
            "lading, skudd og nye våpen."], "check": _always},
    ],
}


def tut_reset(kind):
    act = bpy.data.actions.get(TUT[kind]["action"])
    arm = get_rig()
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    back = bpy.data.actions.get(TUT[kind]["source"])
    if back:
        arm.animation_data.action = back
        arm.animation_data.action_slot = next(s for s in back.slots if not s.name_display.startswith("WPN_"))
    if act:
        bpy.data.actions.remove(act)
    _sync_state["key"] = None
    bpy.context.scene.fpsrig_tut_step = 0


# ---------------------------------------------------------------- UI


class FPSRIG_OT_switch_follow(bpy.types.Operator):
    """Flip the Follow slider of the active control (hand, weapon, camera or weapon part) without it jumping, and key it"""
    bl_idname = "fpsrig.switch_follow"
    bl_label = "Switch Follow (keep pose)"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        pb = context.active_pose_bone
        return pb is not None and follow_prop(pb) is not None

    def execute(self, context):
        pb = context.active_pose_bone
        value = switch_follow(pb.id_data, pb.name)
        self.report({"INFO"}, f"{pb.name}: {follow_prop(pb)} = {value:.0f} (keyed at frame {context.scene.frame_current})")
        return {"FINISHED"}


def _weapon_items(self, context):
    return [("", "Unarmed", "No weapon")] + [(n, n, "") for n in weapon_names()]


class FPSRIG_OT_set_weapon(bpy.types.Operator):
    """Choose which weapon this Action uses (shown automatically; a rigged weapon shares the Action)"""
    bl_idname = "fpsrig.set_weapon"
    bl_label = "Weapon for this Action"
    bl_options = {"REGISTER", "UNDO"}
    weapon: bpy.props.EnumProperty(name="Weapon", items=_weapon_items)

    @classmethod
    def poll(cls, context):
        return _active_action() is not None

    def execute(self, context):
        set_action_weapon(_active_action(), self.weapon)
        return {"FINISHED"}


class FPSRIG_OT_make_weapon_rig(bpy.types.Operator):
    """Build (or update) a weapon rig from the selected part objects: <Weapon>_Frame/_Body/_Receiver plus moving parts"""
    bl_idname = "fpsrig.make_weapon_rig"
    bl_label = "Make / Update Weapon Rig"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return any(o.type in {"MESH", "EMPTY"} for o in context.selected_objects)

    def execute(self, context):
        objs = [o for o in context.selected_objects if o.type in {"MESH", "EMPTY"} and o.name != "WPN_Attach"]
        try:
            wobj = make_weapon_rig(objs)
        except RuntimeError as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}
        _sync_state["key"] = None
        self.report({"INFO"}, f"{wobj.name}: rig ready ({len(objs)} parts)")
        return {"FINISHED"}


class FPSRIG_OT_set_motion(bpy.types.Operator):
    """Set how the active weapon part may move (sets its locks)"""
    bl_idname = "fpsrig.set_motion"
    bl_label = "Set Part Motion"
    bl_options = {"REGISTER", "UNDO"}
    motion: bpy.props.EnumProperty(name="Motion", items=MOTION_ITEMS)
    axis: bpy.props.EnumProperty(name="Axis", items=AXIS_ITEMS, default="Y")

    @classmethod
    def poll(cls, context):
        pb = context.active_pose_bone
        return pb is not None and "Motion" in pb and pb["Motion"] != "ROOT"

    def invoke(self, context, event):
        cur = context.active_pose_bone["Motion"].split()
        self.motion = cur[0]
        self.axis = cur[1] if len(cur) > 1 else ("Y" if cur[0] == "SLIDE" else "X")
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        set_motion(context.active_pose_bone, self.motion, self.axis)
        return {"FINISHED"}


class FPSRIG_OT_export_action(bpy.types.Operator):
    """Export the active Action: Exports/<Action>.fbx (character, Humanoid) + weapon clip if it uses a rigged weapon"""
    bl_idname = "fpsrig.export_action"
    bl_label = "Export this Action"

    def execute(self, context):
        try:
            path = export_active_action()
        except RuntimeError as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}
        self.report({"INFO"}, f"Exported {os.path.basename(path)}")
        return {"FINISHED"}


class FPSRIG_OT_export_all(bpy.types.Operator):
    """Export every Action of this rig (character + weapon clips) to Exports/"""
    bl_idname = "fpsrig.export_all"
    bl_label = "Export all Actions"

    def execute(self, context):
        paths = export_all_actions()
        self.report({"INFO"}, f"Exported {len(paths)} Actions to Exports/")
        return {"FINISHED"}


class FPSRIG_OT_export_weapon_model(bpy.types.Operator):
    """Export the current Action's weapon (model + skeleton at rest) to Exports/Weapons/<Weapon>/"""
    bl_idname = "fpsrig.export_weapon_model"
    bl_label = "Export Weapon Model"

    @classmethod
    def poll(cls, context):
        act = _active_action()
        return act is not None and weapon_rig(act.get("Weapon", "")) is not None

    def execute(self, context):
        path = export_weapon_model(weapon_rig(_active_action()["Weapon"]))
        self.report({"INFO"}, f"Exported {os.path.basename(path)}")
        return {"FINISHED"}


class FPSRIG_OT_fit_to_keys(bpy.types.Operator):
    """Set the Action's Start/End to its first and last keyframe (character and weapon)"""
    bl_idname = "fpsrig.fit_to_keys"
    bl_label = "Fit to keys"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return _active_action() is not None

    def execute(self, context):
        if not fit_range_to_keys(_active_action()):
            self.report({"WARNING"}, "This Action has no keys")
            return {"CANCELLED"}
        return {"FINISHED"}


class FPSRIG_OT_match_end(bpy.types.Operator):
    """Copy the pose of the first frame to the last frame and key it (selected controls, or all if none are selected), so the clip ends where it started"""
    bl_idname = "fpsrig.match_end"
    bl_label = "Match End to Start"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return _active_action() is not None

    def execute(self, context):
        try:
            n = match_end_to_start()
        except RuntimeError as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}
        self.report({"INFO"}, f"Last frame = first frame for {n} controls (keyed)")
        return {"FINISHED"}


class FPSRIG_OT_select_controls(bpy.types.Operator):
    """Select a group of controls (character and the Action's weapon together in Pose Mode)"""
    bl_idname = "fpsrig.select_controls"
    bl_label = "Select Controls"
    bl_options = {"REGISTER", "UNDO"}
    group: bpy.props.EnumProperty(name="Group", items=GROUP_ITEMS)

    @classmethod
    def poll(cls, context):
        return get_rig() is not None

    def execute(self, context):
        chosen = select_controls(self.group)
        self.report({"INFO"}, f"Selected {len(chosen)} controls")
        return {"FINISHED"}


def _tut_steps(context):
    return TUTORIALS[context.scene.fpsrig_tut]


class FPSRIG_OT_tut_nav(bpy.types.Operator):
    """Go to the previous / next tutorial step"""
    bl_idname = "fpsrig.tut_nav"
    bl_label = "Tutorial step"
    delta: bpy.props.IntProperty(default=1)

    def execute(self, context):
        sc = context.scene
        sc.fpsrig_tut_step = max(0, min(len(_tut_steps(context)) - 1, sc.fpsrig_tut_step + self.delta))
        return {"FINISHED"}


class FPSRIG_OT_tut_run(bpy.types.Operator):
    """Prepare (go to the frame and select the control) or do the current tutorial step for you"""
    bl_idname = "fpsrig.tut_run"
    bl_label = "Tutorial action"
    bl_options = {"REGISTER", "UNDO"}
    what: bpy.props.EnumProperty(items=[("prepare", "Prepare", ""), ("do", "Show me", "")])

    def execute(self, context):
        step = _tut_steps(context)[context.scene.fpsrig_tut_step]
        fn = step.get(self.what)
        if fn is None:
            return {"CANCELLED"}
        try:
            fn()
        except Exception as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}
        return {"FINISHED"}


class FPSRIG_OT_tut_reset(bpy.types.Operator):
    """Delete the tutorial's practice Action and start again from step 1"""
    bl_idname = "fpsrig.tut_reset"
    bl_label = "Start over"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        tut_reset(context.scene.fpsrig_tut)
        return {"FINISHED"}


class FPSRIG_PT_panel(bpy.types.Panel):
    bl_label = "FPS Rig"
    bl_idname = "FPSRIG_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "FPS Rig"

    def draw(self, context):
        layout = self.layout
        arm = get_rig()
        if arm is None:
            layout.label(text="No 'Armature' object in this file")
            return
        act = _active_action()
        box = layout.box()
        box.label(text=f"Action: {act.name if act else '(none)'}", icon="ACTION")
        if act:
            row = box.row(align=True)
            row.prop(act, "use_frame_range", text="Manual Range")
            sub = row.row(align=True)
            sub.enabled = act.use_frame_range
            sub.prop(act, "frame_start", text="Start")
            sub.prop(act, "frame_end", text="End")
            row = box.row(align=True)
            row.operator(FPSRIG_OT_fit_to_keys.bl_idname, icon="KEYFRAME")
            row.operator(FPSRIG_OT_match_end.bl_idname, icon="LOOP_BACK")
        box.label(text="Select:")
        row = box.row(align=True)
        for ident, label, _ in GROUP_ITEMS:
            row.operator(FPSRIG_OT_select_controls.bl_idname, text=label).group = ident

        box = layout.box()
        box.label(text="Weapon", icon="MOD_ARMATURE")
        current = (act.get("Weapon", "") if act else "") or "Unarmed"
        box.operator_menu_enum(FPSRIG_OT_set_weapon.bl_idname, "weapon", text=f"Weapon for this Action: {current}")
        box.operator(FPSRIG_OT_make_weapon_rig.bl_idname, icon="BONE_DATA")
        box.operator(FPSRIG_OT_export_weapon_model.bl_idname, icon="EXPORT")

        box = layout.box()
        box.label(text="Active control", icon="CON_CHILDOF")
        pb = context.active_pose_bone
        if pb is not None and follow_prop(pb):
            box.prop(pb, f'["{follow_prop(pb)}"]', text=f"{pb.name}: {follow_prop(pb)}")
        if pb is not None and pb.get("Motion") == "ROOT":
            box.label(text="Whole weapon: scale 0 = hidden, 1 = shown")
        elif pb is not None and "Motion" in pb:
            box.operator(FPSRIG_OT_set_motion.bl_idname, text=f"Motion: {pb['Motion']} (change)")
        if pb is None or (follow_prop(pb) is None and "Motion" not in pb):
            box.label(text="Select a hand, weapon, camera or weapon-part control")
        box.operator(FPSRIG_OT_switch_follow.bl_idname, icon="FILE_REFRESH")

        box = layout.box()
        box.label(text="Export to Unity", icon="EXPORT")
        row = box.row(align=True)
        row.prop(context.scene, "fpsrig_export_character", text="Body", toggle=True)
        row.prop(context.scene, "fpsrig_export_weapon", text="Weapon", toggle=True)
        box.operator(FPSRIG_OT_export_action.bl_idname, icon="ACTION")
        box.operator(FPSRIG_OT_export_all.bl_idname, icon="DOCUMENTS")


class FPSRIG_PT_tutorial(bpy.types.Panel):
    bl_label = "FPS Rig – Tutorial"
    bl_idname = "FPSRIG_PT_tutorial"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "FPS Rig"

    def draw(self, context):
        layout = self.layout
        sc = context.scene
        if get_rig() is None:
            return
        layout.prop(sc, "fpsrig_tut", text="")
        steps = TUTORIALS[sc.fpsrig_tut]
        i = min(sc.fpsrig_tut_step, len(steps) - 1)
        step = steps[i]
        try:
            done = bool(step["check"]())
        except Exception:
            done = False
        box = layout.box()
        box.label(text=f"{step['title']}   ({i + 1}/{len(steps)})", icon="CHECKMARK" if done else "RADIOBUT_OFF")
        col = box.column(align=True)
        for line in step["text"]:
            col.label(text=line)
        if done and step["check"] is not _always:
            box.label(text="Bra! Trykk «Neste».", icon="CHECKMARK")
        row = box.row(align=True)
        if "prepare" in step:
            row.operator(FPSRIG_OT_tut_run.bl_idname, text="Gjør klart", icon="RESTRICT_SELECT_OFF").what = "prepare"
        if "do" in step:
            row.operator(FPSRIG_OT_tut_run.bl_idname, text="Vis meg", icon="PLAY").what = "do"
        row = layout.row(align=True)
        sub = row.row(align=True)
        sub.enabled = i > 0
        sub.operator(FPSRIG_OT_tut_nav.bl_idname, text="Forrige", icon="TRIA_LEFT").delta = -1
        sub = row.row(align=True)
        sub.enabled = i < len(steps) - 1
        sub.operator(FPSRIG_OT_tut_nav.bl_idname, text="Neste", icon="TRIA_RIGHT").delta = 1
        layout.operator(FPSRIG_OT_tut_reset.bl_idname, text="Start på nytt", icon="FILE_REFRESH")


CLASSES = (FPSRIG_OT_switch_follow, FPSRIG_OT_set_weapon, FPSRIG_OT_make_weapon_rig, FPSRIG_OT_set_motion,
           FPSRIG_OT_export_action, FPSRIG_OT_export_all, FPSRIG_OT_export_weapon_model,
           FPSRIG_OT_fit_to_keys, FPSRIG_OT_match_end, FPSRIG_OT_select_controls,
           FPSRIG_OT_tut_nav, FPSRIG_OT_tut_run, FPSRIG_OT_tut_reset, FPSRIG_PT_panel, FPSRIG_PT_tutorial)


def _tut_changed(self, context):
    self.fpsrig_tut_step = 0


SCENE_PROPS = {
    "fpsrig_export_character": lambda: bpy.props.BoolProperty(
        name="Export Body", default=True, description="Export the character clip (Exports/<Action>.fbx)"),
    "fpsrig_export_weapon": lambda: bpy.props.BoolProperty(
        name="Export Weapon", default=True,
        description="Export the weapon clip (Exports/Weapons/<Weapon>/WPN_<Weapon>@<Action>.fbx)"),
    "fpsrig_tut": lambda: bpy.props.EnumProperty(
        name="Tutorial", update=_tut_changed,
        items=[("BODY", "Tutorial 1: Huk og opp (kropp)", ""), ("WEAPON", "Tutorial 2: Pistol, sjekk sliden (våpen)", "")]),
    "fpsrig_tut_step": lambda: bpy.props.IntProperty(name="Tutorial step", default=0, min=0),
}


def register():
    for cls in CLASSES:
        old = getattr(bpy.types, cls.__name__, None)
        if old is not None:  # re-running the text: replace the old registration
            bpy.utils.unregister_class(old)
        bpy.utils.register_class(cls)
    for name, make in SCENE_PROPS.items():
        setattr(bpy.types.Scene, name, make())
    for hl in (bpy.app.handlers.depsgraph_update_post, bpy.app.handlers.load_post):
        for h in [h for h in hl if getattr(h, "__name__", "") == "weapon_sync_handler"]:
            hl.remove(h)
        hl.append(weapon_sync_handler)
    _sync_state["key"] = None


def unregister():
    for hl in (bpy.app.handlers.depsgraph_update_post, bpy.app.handlers.load_post):
        for h in [h for h in hl if getattr(h, "__name__", "") == "weapon_sync_handler"]:
            hl.remove(h)
    for cls in reversed(CLASSES):
        if getattr(bpy.types, cls.__name__, None) is not None:
            bpy.utils.unregister_class(cls)
    for name in SCENE_PROPS:
        if hasattr(bpy.types.Scene, name):
            delattr(bpy.types.Scene, name)


# Registered on file load (text block "Register" option) and when run with Run Script.
register()
