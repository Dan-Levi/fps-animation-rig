"""Export the active Action of the rig to Exports/<ActionName>.fbx for Unity Humanoid.

In Blender: Scripting workspace (or any Text Editor) -> open this text -> Run Script (Alt+P).
Exports only the Mixamo deform skeleton + AnimCamera, baked at 30 fps over the Action's
frame range. Control bones, widgets, cameras and the weapon reference are not exported.

Manual equivalent: File > Export > FBX with the settings listed in Docs/RIG_PLAN.md (section 6).
"""
import os

import bpy

ARMATURE = "Armature"


def export_active_action(filepath=None):
    arm = bpy.data.objects[ARMATURE]
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

    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    prev = (scene.frame_start, scene.frame_end, scene.frame_current, scene.name,
            [o for o in bpy.context.selected_objects], bpy.context.view_layer.objects.active)
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
            # "All Local": cm file units and an unscaled Armature node, matching the source FBX
            apply_scale_options="FBX_SCALE_NONE",
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
        scene.frame_start, scene.frame_end, _, scene.name = prev[0], prev[1], prev[2], prev[3]
        scene.frame_set(prev[2])
        for o in bpy.context.selected_objects:
            o.select_set(False)
        for o in prev[4]:
            o.select_set(True)
        bpy.context.view_layer.objects.active = prev[5]
    print(f"Exported '{act.name}' frames {start}-{end} -> {filepath}")
    return filepath


if __name__ == "__main__":
    export_active_action()
