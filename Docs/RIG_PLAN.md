# FPS Animation Rig – Plan

Status: implemented in `Blender/FPS_Rig.blend` (built by `Blender/scripts/build_fps_rig.py`, Blender 5.0). Blender-side verification done (§7). **Not yet production-ready:** the Unity-side checks in §7 are still open. How to use it: `Docs/ANIMATOR_GUIDE.md`. Review notes: `Docs/RIG_REVIEW.md`.

## 0. Character swap (v1.7): LowPolyGuy

The rig is now built from `Source/Characters/LowPolyGuy_T_Pose.fbx` (Mixamo rig, 65 bones, same names/hierarchy as before; 1 286 verts / 2 532 tris, 4 materials, no UVs yet; weights normalised, no unweighted verts). The file is 6.8 m tall; the build scales the character to `CHARACTER_HEIGHT` = 1.75 m (top of the head) and bakes it, so the rig is in metres as before. The build no longer depends on the character: the mesh is found through its Armature modifier, the eye point is measured from the head bones and mesh (48 % from `Head` to `HeadTop_End`, at the face surface), and ready-made clips are retargeted when the rest pose differs (bone directions, own bone lengths, hips scaled, left hand kept relative to the right). New character: rebuild with another `SRC`.

- `AnimCamera` rest: (0, −0.138, 1.621) m in Blender = Unity (0, 1.621, 0.138). The weapon socket values are unchanged (defined in the hand bone frame).
- `Exports/Character/LowPolyGuy.fbx`: skinned character at rest for the Unity avatar (66 bones incl. `AnimCamera`).
- §1 below describes the first character (`Source/LowPolyMale_Rigged.fbx`).

## 1. Source inspection (Source/LowPolyMale_Rigged.fbx, first character)

| Item | Finding |
|---|---|
| File | Binary FBX 7.7, FBX SDK 2020.2 (3ds Max export of a Mixamo character), Y-up, cm units |
| Objects | `Armature` (65 bones) + `SM_LowPolyMale` (1036 verts, 2040 tris, 1 material, 1 UV map, no shape keys) |
| Blender import | Armature object gets rot X 90°, scale 0.01 (Y-up, cm FBX). The rig build **applies the scale** (armature + mesh) so the rig works in metres; the 90° rotation is kept because it cancels the FBX axis conversion. Character is 1.76 m tall, faces −Y, feet on Z=0 |
| Skeleton | Standard Mixamo: `mixamorig:Hips` root → Spine/Spine1/Spine2 → Neck/Head/HeadTop_End, Shoulder/Arm/ForeArm/Hand, 5 fingers × 4 bones, UpLeg/Leg/Foot/ToeBase/Toe_End |
| Rest pose | T-pose. Elbows pre-bent ~16° (backward), knees ~4.5° (forward) – good IK bend hints |
| Bone axes | Spine/neck/head: Y up, Z forward. Fingers curl on local **+X** (both hands) |
| Weights | All 1036 verts weighted, all normalized. 52 weighted bones; the 13 `*_End`/`*4` leaf bones are unweighted (normal). 53 verts have >4 influences (max 7) – Unity's default "4 bones" skin quality slightly simplifies these; not an animation issue |
| Extra data | A 2-frame `mixamo.com` take (near-bind pose). Not used; removed from the rig file |
| Round trip | Blender FBX export (settings in §6): cm units, identity `Armature` node, Hips local translation identical to the source. Rest rotations: untouched skeleton re-exports within 0.001° of the source; the rigged file (constraints active) within 0.05° – float32 precision level, sub-millimetre |

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
| `CTRL_Hips` | `Hips` | Rotation only (pelvis tilt/swing). Upper body keeps its orientation but its base moves slightly with the pelvis. Move the body with `CTRL_Torso` |
| `CTRL_Spine`, `CTRL_Chest`, `CTRL_UpperChest` | `Spine`, `Spine1`, `Spine2` | FK rotation |
| `CTRL_Neck`, `CTRL_Head` | `Neck`, `Head` | FK rotation |
| `CTRL_Shoulder.L/R` | `Shoulder` | Clavicle shrug |
| `CTRL_Hand_IK.R` | right arm + `Hand` | **Follow Weapon** 1 = carried by `CTRL_Weapon` (default), 0 = free |
| `CTRL_Hand_IK.L` | left arm + `Hand` | **Follow Weapon** 1 = follows the weapon as held in the right hand (`WPN_Socket`) (default), 0 = free |
| `CTRL_Elbow_Pole.L/R` | elbow direction | Follows upper chest |
| `CTRL_Foot_IK.L/R` | leg chain + `Foot` | Flat, world-aligned, pivot at the ankle. Planted feet. No heel/toe roll (§8) |
| `CTRL_Toe.L/R` | `ToeBase` | Toe bend |
| `CTRL_Knee_Pole.L/R` | knee direction | Follows its foot |
| `CTRL_Grip.L/R` | 4 fingers | Rotate X = whole-hand fist (joint share 1 / 1 / 0.7), Z = fan spread (+Z opens, same on both hands) |
| `CTRL_Index/Middle/Ring/Pinky.L/R` | that finger | Rotate X = curl all 3 joints equally, Z = side-to-side at the knuckle (direction is mirrored between hands – rotate visually) |
| `CTRL_Thumb.L/R` | thumb | Rotate X = curl across the palm toward the pinky (metacarpal gets half), Z = +away from the palm / −wrap around a handle (same on both hands). Thumb controls have their own roll; `MCH_Thumb1–3` hand the rotation to the untouched deform bones |
| `CTRL_<Finger>1-3.L/R` | single joints | Fine adjustment, layered on top of curl |
| `CTRL_Weapon` | right hand (and through it the weapon) | Grab handle for the weapon. **Follow Chest** 1 = moves with the upper body. Weapon models parent to `WPN_Attach`, not here (§5) |
| `CTRL_Camera` | `AnimCamera` | Slider **Follow Head** (default 0) |

Space-switch sliders use an Armature constraint whose two weights are set by plain (non-Python) drivers. They are meant to be set once per Action; animating them is possible but can pop.

Bone collections: **Main**, **Fingers**, **Finger Detail**, plus hidden **Deform (Mixamo)** and **Mechanism**.

## 4. Camera

Uses: accurate FPS preview in Blender, optional animation-driven camera offsets, and cutscenes where the animation temporarily owns the camera.

- Exported bone `AnimCamera` at the eyes: (0, −0.138, 1.621) m (LowPolyGuy; was (0, −0.070, 1.645) on the first character). **Top-level** (sibling of `Hips` under the `Armature` node) – i.e. it lives in **character-root space**, the same space the Hips curve lives in.
- In the exported FBX/Unity it has **identity rest rotation** relative to the character root (verified: FBX Lcl Rotation 0) – +Z = character forward, +Y = up. Rest local position (0, 1.621, 0.138) m.
- Why top-level and not a child of `Head`/`Hips`: a child would inherit breathing, head bob and retargeting differences, and the "offset" would have to be reconstructed by subtracting the head pose. Top-level means the curve already *is* the authored camera, with zero inherited motion. Head-following is opt-in (**Follow Head**) and gets baked into the curve only when chosen.
- Controls: `CTRL_Camera` (animate) → `AnimCamera` (exported). `MCH_Space_Camera` blends between `CTRL_Root` (default) and the deform `Head` (**Follow Head** = 1, e.g. knockdown/get-up cutscenes).
- `FPS_View` (Blender camera, 60° vertical FOV = Unity default, 16:9) rides on `AnimCamera`, so it shows *neutral gameplay camera + authored offset*. It does not show player look input or controller-driven crouch height.

Intended Unity use (to implement and verify in Unity – not part of this repo):

- `offset = Inverse(restLocal) * currentLocal`, where `restLocal` = position (0, 1.621, 0.138), identity rotation.
- **Gameplay** (player owns the camera): `camera = playerCamera * offset`. With `CTRL_Camera` untouched the offset is identity, so gameplay is unaffected.
- **Cutscene** (animation owns the camera): `camera = characterRoot * currentLocal`, blended in/out with a weight. Player look is ignored while the weight is 1.
- Root-motion caveat: like Hips, `AnimCamera` contains any travel of the body in Blender (moving `CTRL_Root`/`CTRL_Torso` for locomotion). Unity applies root motion to the GameObject but `AnimCamera` is a plain transform, so for clips that use **Apply Root Motion** the camera would be displaced twice. For camera-owned clips either keep the motion in-place (Bake Into Pose) or have the camera script subtract the root motion delta.
- Hookup: Humanoid clips only carry non-humanoid transforms that exist on the character and are enabled in the clip's **Mask → Transform**. The source character has no `AnimCamera`, so add a child `Armature/AnimCamera` transform (or import the character from a rig export) at the rest values above.

## 5. Weapons and tools

Assumption (to confirm against the Unity project): at runtime the weapon is attached to the **right-hand bone** through a socket transform.

- `WPN_Socket` (hidden bone, not exported) is rigidly parented to `mixamorig:RightHand` – the Blender equivalent of that runtime socket. The visible empty `WPN_Attach` sits on it; weapon models (and the placeholders in the **Weapon References** collection: rifle, pistol, shotgun, bat, crowbar, key) parent to `WPN_Attach`, so the weapon you see in Blender is exactly where a right-hand socket puts it in Unity.
- `CTRL_Weapon` is the animator's grab handle: it carries the right hand (**Follow Weapon** on the right hand), and the right hand carries the weapon. The left hand follows `WPN_Socket` – the weapon as actually held – so foregrip placement stays consistent even if the right hand is offset or cannot reach.
- Rest grip offset = a pistol-grip hand pose. Socket axes match Unity conventions: +Z = barrel, +Y = weapon up, pivot = grip point. A weapon prefab authored with +Z forward and its pivot at the pistol grip needs no extra offset.
- Socket transform for Unity (child of `mixamorig:RightHand`), derived from the rig and cross-checked against the FBX node; the X-mirror conversion to Unity is standard but should be verified once in Unity by eye:
  - localPosition (m): (0.0000, 0.0660, 0.0250)
  - localRotation (x, y, z, w): (−0.48823, 0.62694, 0.36381, 0.48602) ≈ Euler (291.45, 135.96, 315.00)
- Not supported in v1: the weapon leaving the right hand (hand-overs, left-hand-only weapons). Unity runtime left-hand IK, if used, will override the authored left hand.
- Unity Humanoid retargeting (muscle limits, arm stretch) can move hands by a few millimetres–centimetres; small foregrip gaps in Unity are expected and usually fixed with runtime left-hand IK.

## 6. Export to Unity

Settings (in `Blender/scripts/fps_rig_tools.py`, embedded in the .blend as the self-registering **FPS Rig** sidebar panel: *Export this Action* / *Export all Actions*):

- Selection: the armature only. Object types: Armature
- Scale: **FBX Units Scale**, Forward −Z, Up Y, Apply Transform off. With the rig in metres (armature scale 1) this writes metre units and an **unscaled** `Armature` node; Hips local (0, 0.988, 0.002) m – the same Unity transforms as the source FBX (which is in cm). Rule: the root node must end up unscaled; a 0.01/100 scale on it is a common source of Humanoid/root-motion scale problems.
- Armature: **Only Deform Bones** on, **Add Leaf Bones** off, primary Y / secondary X
- Animation: Bake on, NLA strips off, All Actions off, Force Start/End keying on, Simplify 0, 30 fps
- Output: `Exports/<ActionName>.fbx`

Result: an `Armature` node (identity) with the 65 Mixamo bones + `AnimCamera`. No control bones, socket, widgets, cameras or weapon. The take is named after the Action. The only structural difference from the source FBX is the extra identity `Armature` node (Humanoid maps bones by name, so this is expected to be harmless – verify in Unity).

Unity: Rig = Humanoid, Avatar = *Copy From Other Avatar* (the existing Mixamo avatar).

## 7. Verification

Done in Blender (scripted checks):

1. With all controls at rest, every deform bone matches its original rest pose within 0.05° / 0.004 cm (measured in float64 from the exported FBX; Blender's float32 pose matrices can't resolve finer).
2. Crouch: lowering `CTRL_Torso` 30 cm keeps the feet within 0.1 mm, knees bend forward.
3. Fingers: curl is additive (master + detail + grip) with a 1 / 1 / 0.7 joint share, fan spread opens on both hands, thumb curl distributes 0.5/1/1 across the palm.
4. Weapon: in the example pose `WPN_Socket` and `CTRL_Weapon` coincide; hands follow; `Follow Weapon` = 0 releases a hand.
5. Camera: `Follow Head` = 0 → head motion does not move `AnimCamera`; = 1 → it does.
6. Export: an animated test Action re-imports with all deform bones matching the rig to 0.02 mm (rotation differences below the float32 resolution of ~0.04°), no control bones exported; FBX structure matches the source conventions (§6).

Still open – needs the Unity project:

- Humanoid import of `Exports/Pistol_Draw.fbx` (test animation) with *Copy From Other Avatar* on the existing avatar.
- Compare `AnimCamera` rest position with the current neutral FPS camera.
- Confirm the weapon attachment convention (§5) and socket values.
- Implement the `AnimCamera` offset/cutscene logic (§4).

## 7b. Start poses, tools and test animation (v1.1)

- Actions (fake user, Follow sliders keyed with constant interpolation): `Unarmed_Idle`, `Guard_Idle`, `Melee_Bat_Idle`, `Melee_Crowbar_Idle`, `Pistol_Idle_Hip` (60-frame loops, cyclic F-curves), `Pistol_Draw` (24 frames, pose marker `WeaponShow` at 8), `Example_FPS_Ready`. The file opens on `Unarmed_Idle` with all weapon references hidden.
- **FPS Rig** panel: *Switch Follow (keep pose)* flips a Follow slider without the control moving and keys slider + transform (old value held on the previous frame); export buttons. The build script uses the same functions for the start poses and `Pistol_Draw`.
- `FPS_View` shows a centre cross (composition guide) = gameplay crosshair.
- Unity-side guide: `Docs/UNITY_INTEGRATION.md`.

## 7c. Weapon rigs (v1.2)

- Each weapon with moving parts is its own small armature `WPN_<Weapon>` (collection `Weapons/WPN_<Weapon>`), parented to `WPN_Attach`. Its armature space equals the socket frame (Y up, Z barrel), so the exported weapon root has no rotation/scale (+Z barrel, +Y up in Unity).
- Built by **Make / Update Weapon Rig** (`fps_rig_tools.make_weapon_rig`) from part objects modelled at the origin (grip), barrel −Y, up +Z, one object per moving part, pivot = object origin, names `<Weapon>_<Part>`. Works for any weapon type: motion type from the part name (Slide / Rotate / Detachable / Free, editable), hierarchy from object parenting, object scale baked (3ds Max/FBX imports), pivot axes taken relative to the main part. Update keeps animation (bone names = part names).
- `CTRL_Root` drives the weapon root (scale 0 hides the whole weapon, e.g. before a draw). Detachable parts can also be hidden with scale 0; scale keys use constant interpolation and export to Unity.
- Controls `CTRL_<Part>` drive deform bones (Copy Transforms); detachable parts get **Follow Left Hand** (Copy Transforms to the character's `PROP_Hand.L`, a left-hand prop socket mirroring the right-hand grip).
- One Action per clip holds both character and weapon animation (separate action slots). The panel's **Weapon for this Action** + a persistent handler show the right weapon and share the Action with its rig (also after duplicating an Action).
- Export: character clip as before; weapon clip `Exports/Weapons/<W>/WPN_<W>@<Action>.fbx` (deform bones relative to the weapon root, baked on a temporary unconstrained copy); weapon model `WPN_<W>.fbx` (Generic). Examples: `WPN_Pistol` (Frame/Slide/Trigger/Magazine/Muzzle/Eject) with `Pistol_Fire` and `Pistol_Reload`; `WPN_Shotgun` (Receiver/Pump/Trigger/Shell) rigged with the same tool.

## 7d. Workflow helpers (v1.3)

- The timeline follows the active Action's frame range (same persistent handler, only when the Action or its range changes). The panel shows the Action's Start/End/Manual Range, plus **Fit to keys** (range = first..last key over all slots).
- **Match End to Start**: copies the first-frame pose (transforms, Follow sliders, part scale) of the selected controls (or all character + weapon controls) to the last frame and keys it.
- **Select: All / Body / Fingers / Weapon**: character + the Action's weapon rig in multi-object Pose Mode; controls in hidden bone collections are skipped.
- Export toggles **Body** / **Weapon** (scene properties) choose the character clip, the weapon clip or both.
- The "Animation" workspace: small 3D view through `FPS_View`, Dope Sheet in Action Editor mode.
- **FPS Rig – Tutorial** sub-panel: two data-driven, step-by-step tutorials (`Tut_Crouch`, `Tut_PistolCheck`) with automatic step checks and *Prepare* / *Show me* buttons. They use the same functions as the panel. *Start over* deletes the practice Action. Practice exports are git-ignored.

## 7e. M1911 (v1.5)

- The placeholder pistol is replaced by the user's M1911 from 3ds Max: `Source/Weapons/M1911_original_max.fbx` → `Blender/scripts/prepare_m1911.py` → `Source/Weapons/M1911.fbx` (parts `M1911_*`, trigger and hammer split from the frame, magazine pivot on top and tilted 12° with the grip, Muzzle/Eject added; cm, Y-up, readable by Max). The build imports it and rigs `WPN_M1911`; the pistol clips keep their names (`Pistol_*`) with Weapon = M1911.
- M1911 specifics: the trigger slides (Motion SLIDE Y); the hammer is modelled cocked, falls on the shot and is pushed back by the slide; the magazine leaves along the well (`MAG_AXIS`).
- Weapon right side = −X in the modelling frame (barrel −Y, up +Z); `_Eject` points sit there (the old placeholders had them on the left).

## 7f. Imported clips (v1.6)

- `Pistol_Idle_Hip` now comes from the user's loop `Source/Animations/pistol_idle_loop_fit.glb` (same Mixamo skeleton and rest pose, 30 fps, 50-frame seamless loop). The build samples it (`sample_clip`: source pose relative to the source rest, applied to this rig's rest, so import axes and bone orientations do not matter) and sets every control per frame (`pose_from_world`): torso/hips, spine, neck, head, shoulders, hand IK (weapon placed from the right hand via the socket), elbow/knee poles (with the rest pole offset of each limb), foot IK, toes and every finger/thumb detail control. Keys on every frame, cyclic.
- Accuracy: hands, fingers, spine, feet exact; elbows/knees within 4.3 mm (IK); exported FBX vs the GLB within 4.3 mm.
- The other pistol clips still use the procedural hip pose; their weapon pose differs from the idle's first frame by about 4 cm / 14°.

## 8. Out of scope for this version

- Foot: no heel/toe roll pivots or roll slider – the foot rotates around the ankle, so heel-lifts and tip-toe need foot rotation plus a counter-move, or `CTRL_Toe`. No knee-snap softening: near full leg extension the IK can pop. No automatic floor contact.
- IK/FK arm switching, stretchy limbs, space switching without pops (sliders are meant to be set once per Action).
- Weapon hand-overs / left-hand-held weapons.
- Unity scripts (camera offset, socket setup).
