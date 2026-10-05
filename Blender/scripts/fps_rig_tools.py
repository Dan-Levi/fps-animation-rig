"""FPS Rig tools: an "FPS Rig" tab in the 3D View sidebar (N panel).

- Switch Follow (keep pose): flip a control's Follow slider without the control jumping.
- Export this Action / Export all Actions: one FBX per Action in Exports/, skeleton only.

Embedded in Blender/FPS_Rig.blend as a text block that registers itself when the file is
opened (if Blender blocks scripts: click "Allow Execution", or open the text and Run Script).
The rig works without this panel; see Docs/ANIMATOR_GUIDE.md for the manual export settings.
"""
import os

import bpy
from bpy_extras import anim_utils

ARMATURE = "Armature"
# control -> its space-switch slider
FOLLOW_PROPS = {
    "CTRL_Hand_IK.L": "Follow Weapon",
    "CTRL_Hand_IK.R": "Follow Weapon",
    "CTRL_Weapon": "Follow Chest",
    "CTRL_Camera": "Follow Head",
}


# ---------------------------------------------------------------- helpers
def get_rig():
    return bpy.data.objects.get(ARMATURE)


def action_fcurves(arm):
    """F-curves of the rig's active Action (Blender 4.4+ slotted actions)."""
    ad = arm.animation_data
    if not ad or not ad.action or not ad.action_slot:
        return []
    cb = anim_utils.action_get_channelbag_for_slot(ad.action, ad.action_slot)
    return cb.fcurves if cb else []


def key_control(arm, name, frame):
    """Key location, rotation and (if any) the Follow slider of one control."""
    pb = arm.pose.bones[name]
    pb.keyframe_insert("location", frame=frame)
    pb.keyframe_insert("rotation_quaternion" if pb.rotation_mode == "QUATERNION" else "rotation_euler", frame=frame)
    prop = FOLLOW_PROPS.get(name)
    if prop:
        pb.keyframe_insert(f'["{prop}"]', frame=frame)
        path = f'pose.bones["{name}"]["{prop}"]'
        for fc in action_fcurves(arm):
            if fc.data_path == path:
                for kp in fc.keyframe_points:
                    kp.interpolation = "CONSTANT"  # sliders switch, never blend


def switch_follow(arm, name, value=None, frame=None, key=True):
    """Set a Follow slider (toggle if value is None) keeping the control's world transform.

    With key=True: the old slider + transform are held on frame-1 and the new ones keyed on frame.
    """
    scene = bpy.context.scene
    pb = arm.pose.bones[name]
    prop = FOLLOW_PROPS[name]
    frame = scene.frame_current if frame is None else frame
    if value is None:
        value = 0.0 if pb[prop] >= 0.5 else 1.0
    animated = key and arm.animation_data and arm.animation_data.action
    if animated:
        scene.frame_set(frame - 1)
        key_control(arm, name, frame - 1)
    scene.frame_set(frame)
    world = arm.matrix_world @ pb.matrix
    pb[prop] = value
    arm.update_tag()
    bpy.context.view_layer.update()
    pb.matrix = arm.matrix_world.inverted() @ world
    bpy.context.view_layer.update()
    if key:
        key_control(arm, name, frame)
    return value


def export_active_action(filepath=None):
    """Export the rig's active Action to Exports/<ActionName>.fbx (skeleton only, baked)."""
    arm = get_rig()
    act = arm.animation_data.action if arm.animation_data else None
    if act is None:
        raise RuntimeError("The rig has no active Action. Assign one in the Action Editor first.")
    scene = bpy.context.scene
    start, end = (int(round(f)) for f in act.frame_range)
    if filepath is None:
        base = bpy.path.abspath("//") or os.getcwd()
        out_dir = os.path.normpath(os.path.join(base, "..", "Exports"))
        os.makedirs(out_dir, exist_ok=True)
        filepath = os.path.join(out_dir, bpy.path.clean_name(act.name) + ".fbx")

    prev_obj = bpy.context.object
    prev_mode = prev_obj.mode if prev_obj else "OBJECT"
    if prev_obj and prev_mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    prev = (scene.frame_start, scene.frame_end, scene.frame_current, scene.name,
            list(bpy.context.selected_objects), bpy.context.view_layer.objects.active)
    try:
        scene.frame_start, scene.frame_end = start, end
        scene.name = act.name  # single-take FBX exports are named after the scene
        for o in bpy.context.selected_objects:
            o.select_set(False)
        arm.select_set(True)
        bpy.context.view_layer.objects.active = arm
        bpy.ops.export_scene.fbx(
            filepath=filepath,
            use_selection=True,
            object_types={"ARMATURE"},
            # Armature is in metres with scale 1: metre file units, unscaled Armature node
            apply_scale_options="FBX_SCALE_UNITS",
            axis_forward="-Z",
            axis_up="Y",
            bake_space_transform=False,
            use_armature_deform_only=True,
            add_leaf_bones=False,
            primary_bone_axis="Y",
            secondary_bone_axis="X",
            armature_nodetype="NULL",
            bake_anim=True,
            bake_anim_use_all_bones=True,
            bake_anim_use_nla_strips=False,
            bake_anim_use_all_actions=False,
            bake_anim_force_startend_keying=True,
            bake_anim_step=1.0,
            bake_anim_simplify_factor=0.0,
        )
    finally:
        scene.frame_start, scene.frame_end, scene.name = prev[0], prev[1], prev[3]
        scene.frame_set(prev[2])
        for o in bpy.context.selected_objects:
            o.select_set(False)
        for o in prev[4]:
            o.select_set(True)
        bpy.context.view_layer.objects.active = prev[5]
        if prev_obj and prev_mode != "OBJECT" and bpy.context.view_layer.objects.active == prev_obj:
            bpy.ops.object.mode_set(mode=prev_mode)  # back to Pose Mode etc.
    print(f"Exported '{act.name}' frames {start}-{end} -> {filepath}")
    return filepath


def rig_actions(arm):
    """Actions made for this rig (they animate CTRL_ bones)."""
    out = []
    for act in bpy.data.actions:
        for slot in act.slots:
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
            paths.append(export_active_action())
    finally:
        ad.action = prev[0]
        if prev[0]:
            ad.action_slot = prev[1]
    return paths


# ---------------------------------------------------------------- UI
class FPSRIG_OT_switch_follow(bpy.types.Operator):
    """Flip the Follow slider of the active control (hand, weapon or camera) without it jumping, and key it"""
    bl_idname = "fpsrig.switch_follow"
    bl_label = "Switch Follow (keep pose)"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        pb = context.active_pose_bone
        return pb is not None and pb.name in FOLLOW_PROPS

    def execute(self, context):
        arm = get_rig()
        name = context.active_pose_bone.name
        value = switch_follow(arm, name)
        self.report({"INFO"}, f"{name}: {FOLLOW_PROPS[name]} = {value:.0f} (keyed at frame {context.scene.frame_current})")
        return {"FINISHED"}


class FPSRIG_OT_export_action(bpy.types.Operator):
    """Export the active Action to Exports/<ActionName>.fbx (skeleton only, for Unity Humanoid)"""
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
    """Export every Action of this rig, one FBX each, to Exports/"""
    bl_idname = "fpsrig.export_all"
    bl_label = "Export all Actions"

    def execute(self, context):
        paths = export_all_actions()
        self.report({"INFO"}, f"Exported {len(paths)} Actions to Exports/")
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
        act = arm.animation_data.action if arm.animation_data else None
        layout.label(text=f"Action: {act.name if act else '(none)'}", icon="ACTION")

        box = layout.box()
        box.label(text="Follow sliders", icon="CON_CHILDOF")
        pb = context.active_pose_bone
        if pb is not None and pb.name in FOLLOW_PROPS:
            box.prop(pb, f'["{FOLLOW_PROPS[pb.name]}"]', text=f"{pb.name}: {FOLLOW_PROPS[pb.name]}")
        else:
            box.label(text="Select a hand, weapon or camera control")
        box.operator(FPSRIG_OT_switch_follow.bl_idname, icon="FILE_REFRESH")

        box = layout.box()
        box.label(text="Export to Unity", icon="EXPORT")
        box.operator(FPSRIG_OT_export_action.bl_idname, icon="ACTION")
        box.operator(FPSRIG_OT_export_all.bl_idname, icon="DOCUMENTS")


CLASSES = (FPSRIG_OT_switch_follow, FPSRIG_OT_export_action, FPSRIG_OT_export_all, FPSRIG_PT_panel)


def register():
    for cls in CLASSES:
        old = getattr(bpy.types, cls.__name__, None)
        if old is not None:  # re-running the text: replace the old registration
            bpy.utils.unregister_class(old)
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(CLASSES):
        if getattr(bpy.types, cls.__name__, None) is not None:
            bpy.utils.unregister_class(cls)


# Registered on file load (text block "Register" option) and when run with Run Script.
register()
