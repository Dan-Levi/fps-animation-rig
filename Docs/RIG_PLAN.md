# FPS Animation Rig – Plan

Status: implemented in `Blender/FPS_Rig.blend` (built by `Blender/scripts/build_fps_rig.py`, Blender 5.0). Blender-side verification done (§7); Unity-side checks pending. How to use it: `Docs/ANIMATOR_GUIDE.md`.

## 1. Source inspection (Source/LowPolyMale_Rigged.fbx)

| Item | Finding |
|---|---|
| File | Binary FBX 7.7, FBX SDK 2020.2 (3ds Max export of a Mixamo character), Y-up, cm units |
| Objects | `Armature` (65 bones) + `SM_LowPolyMale` (1036 verts, 2040 tris, 1 material, 1 UV map, no shape keys) |
| Blender import | Armature object gets rot X 90°, scale 0.01 (normal for cm-based FBX). Character is 1.76 m tall, faces −Y, feet on Z=0 |
| Skeleton | Standard Mixamo: `mixamorig:Hips` root → Spine/Spine1/Spine2 → Neck/Head/HeadTop_End, Shoulder/Arm/ForeArm/Hand, 5 fingers × 4 bones, UpLeg/Leg/Foot/ToeBase/Toe_End |
| Rest pose | T-pose. Elbows pre-bent ~16° (backward), knees ~4.5° (forward) – good IK bend hints |
| Bone axes | Spine/neck/head: Y up, Z forward. Fingers curl on local **+X** (both hands) |
| Weights | All 1036 verts weighted, all normalized. 52 weighted bones; the 13 `*_End`/`*4` leaf bones are unweighted (normal). 53 verts have >4 influences (max 7) – Unity's default "4 bones" skin quality slightly simplifies these; not an animation issue |
| Extra data | A 2-frame `mixamo.com` take (near-bind pose). Not used; removed from the rig file |
| Round trip | Blender FBX export (settings in §6) re-imports with all 65 bones, identical hierarchy, max deviation 0.000008 m |

Unity project: not available to this session, so the neutral FPS camera could not be measured. The camera is placed at the eyes (§4) and must be checked against the Unity camera before final sign-off.

## 2. Core approach

**One armature, one Action.** Controls are extra non-deform bones inside the same armature as the Mixamo skeleton.

- Mixamo bones keep their names, hierarchy, rest pose and weights. They only get constraints.
- Animators key only `CTRL_*` bones. Deform bones are hidden.
- Deform bones follow controls through Blender-native constraints (Copy Rotation, Copy Transforms, IK).
- Export uses Blender's FBX exporter with **Only Deform Bones** + **Bake Animation**. The exporter samples the evaluated pose every frame, so baking happens during export. No separate bake step, no second Action.
- Non-hip deform bones only receive **rotations** (Unity Humanoid ignores their translation, so no stretch is allowed).

## 3. Controls

Colours: center = yellow, left = blue, right = red, fingers = green, camera = purple, weapon = orange.

| Control | Drives | Notes |
|---|---|---|
| `CTRL_Root` | everything | On the ground. Keep at origin for in-place clips |
| `CTRL_Torso` | body (COG) | Move down to crouch – feet stay planted |
| `CTRL_Hips` | `Hips` | Pelvis only; upper body stays put |
| `CTRL_Spine`, `CTRL_Chest`, `CTRL_UpperChest` | `Spine`, `Spine1`, `Spine2` | FK rotation |
| `CTRL_Neck`, `CTRL_Head` | `Neck`, `Head` | FK rotation |
| `CTRL_Shoulder.L/R` | `Shoulder` | Clavicle shrug |
| `CTRL_Hand_IK.L/R` | arm chain + `Hand` | Slider **Follow Weapon** (0 = world/root, 1 = moves with weapon) |
| `CTRL_Elbow_Pole.L/R` | elbow direction | Follows upper chest |
| `CTRL_Foot_IK.L/R` | leg chain + `Foot` | Flat, world-aligned. Planted feet |
| `CTRL_Toe.L/R` | `ToeBase` | Toe bend |
| `CTRL_Knee_Pole.L/R` | knee direction | Follows its foot |
| `CTRL_Grip.L/R` | 4 fingers | Rotate X = whole-hand fist |
| `CTRL_Index/Middle/Ring/Pinky.L/R` | that finger | Rotate X = curl all 3 joints, Z = spread |
| `CTRL_Thumb.L/R` | thumb | Rotate X = curl, Z = spread/opposition |
| `CTRL_<Finger>1-3.L/R` | single joints | Fine adjustment, layered on top of curl |
| `CTRL_Weapon` | weapon reference | Slider **Follow Chest** (1 = weapon moves with upper body). Parent weapon models here |
| `CTRL_Camera` | `AnimCamera` | Slider **Follow Head** (default 0) |

Space-switch sliders use an Armature constraint whose two weights are set by plain (non-Python) drivers. They are meant to be set once per Action; animating them is possible but can pop.

Bone collections: **Main**, **Fingers**, **Finger Detail**, plus hidden **Deform (Mixamo)** and **Mechanism**.

## 4. Camera

- Exported bone `AnimCamera`, top-level (no parent), at the eyes: (0, −0.070, 1.645) m.
- Rest orientation equals `mixamorig:Head` (Y up, Z forward), so in Unity it has the same +Z forward / +Y up convention as the Mixamo bones.
- Not parented to the head: its local transform is purely the authored camera offset. Breathing/head motion never moves the gameplay camera unless the animator chooses **Follow Head**.
- Unity model: `gameplay camera + (AnimCamera pose − AnimCamera rest)`. At rest the offset is zero.
- `FPS_View` Blender camera rides on `AnimCamera` (60° vertical FOV, Unity's default, 16:9) for first-person preview. `External_View` gives a full-body view.
- Unity hookup (to verify in Unity): the character model needs a transform with the same path as in the clips, which is easiest by importing the character once from this rig file's export. The clip import must include `AnimCamera` in its mask (Humanoid keeps non-humanoid transforms only when masked in).

## 5. Weapons and tools

- `CTRL_Weapon` is a reference/socket. It holds a placeholder (`REF_Weapon`) that can be replaced by any weapon or tool model parented to the control.
- Default rest: at the right hand grip, pointing forward.
- Both hands follow the weapon by default (good for rifles, reloads, recoil, two-handed melee). Set **Follow Weapon** to 0 for unarmed actions or interactions.
- The weapon is not exported. In Unity, weapons attach to the right-hand bone as usual.

## 6. Export to Unity

Settings (also in the script `Blender/scripts/export_action_to_unity.py`, embedded in the .blend as a text block):

- Selection: the armature only. Object types: Armature
- Scale: *FBX Units Scale*, Forward −Z, Up Y, Apply Transform off
- Armature: **Only Deform Bones** on, **Add Leaf Bones** off, primary Y / secondary X
- Animation: Bake on, NLA strips off, All Actions off, Force Start/End keying on, Simplify 0, 30 fps
- Output: `Exports/<ActionName>.fbx`

Result: the 65 Mixamo bones + `AnimCamera`. No control bones, widgets, cameras or weapon.

Unity: Rig = Humanoid, Avatar = *Copy From Other Avatar* (the existing Mixamo avatar).

## 7. Verification (done in Blender here)

1. With all controls at rest, every deform bone matches its original rest pose.
2. Crouch test: lowering `CTRL_Torso` keeps feet planted, knees bend forward.
3. Finger curl closes toward the palm on both hands.
4. Export a test Action, re-import it, and compare deform-bone world transforms per frame with the rig.

Still requires Unity: Humanoid import of an exported clip on the existing avatar, and checking the camera position.

## 8. Out of scope for this version

Foot roll pivots, IK/FK arm switching, stretchy limbs, automatic weapon-hand snapping, Unity scripts.
