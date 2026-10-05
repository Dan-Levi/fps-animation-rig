# Rig Review – production readiness

Focused review of `Blender/FPS_Rig.blend` before calling it production-ready. Verdict: **Blender side ready; production sign-off waits on the Unity checks at the end.**

## 1. Camera hierarchy (AnimCamera)

**Kept top-level** (child of the `Armature` root node, sibling of `Hips`). Alternatives considered:

| Option | Gameplay offset | Cutscene ownership | Inherited motion |
|---|---|---|---|
| Child of `Head` | offset must be reconstructed by removing head motion; Humanoid retargeting changes the head pose in Unity | camera follows head always | breathing, head bob, retarget differences |
| Child of `Hips` | same problem with hip motion | – | locomotion bob |
| **Top-level (current)** | curve *is* the offset (identity at rest) | curve is a complete character-space camera pose | **none** unless **Follow Head** is chosen |

Verified in the exported FBX: rest rotation identity relative to the character root (+Z forward, +Y up), position (0, 1.645, 0.07) m. Head-following is opt-in and baked only when chosen. Added to docs: the offset/ownership formulas, the crouch-preview limitation, and the **root-motion caveat** (the camera curve contains body travel; Unity applies root motion to the GameObject, so camera-owned clips that use root motion need the script to subtract it, or stay in-place).

## 2. Armature scale 0.01 / rotation X 90°

- The object transform is how Blender represents a Y-up centimetre FBX; it cancels on export (the `Armature` node exports with zero rotation). **Kept.**
- **Fixed:** export used *FBX Units Scale*, which wrote metres plus a **0.01-scaled `Armature` node**. Switched to **All Local**: centimetre units, identity `Armature` node, Hips local translation identical to the source FBX. Only remaining structural difference: the extra identity `Armature` node (Humanoid maps by bone name; verify in Unity).

## 3. Weapon / hand IK / runtime attachment

- **Fixed conflict:** the weapon used to sit on `CTRL_Weapon` while the right hand only chased it with IK. Any right-hand offset or reach limit made Blender's weapon disagree with a runtime right-hand socket (the example pose itself had this).
- Now: hidden bone `WPN_Socket` rigidly on `mixamorig:RightHand`, plus a visible `WPN_Attach` empty for weapon models. `CTRL_Weapon` carries the right hand; the left hand follows the socket. Socket axes: +Z barrel, +Y up, pivot at the grip. Unity local values documented in RIG_PLAN §5.
- Assumption to confirm: runtime attaches weapons to the right-hand bone. Not supported: weapon hand-overs / left-hand weapons.

## 4. Fingers

| Check | Result |
|---|---|
| Curl (X) | same direction on both hands; 3 joints equal; additive with grip and detail controls (no double transform – verified 60+20 = 80° etc.) |
| Spread | **was misleading:** per-finger Z shifts the finger sideways and is mirrored between hands. **Added** Grip Z fan spread (index/middle toward thumb, ring/pinky away; +Z opens on both hands). Per-finger Z documented as sideways/visual |
| Thumb | **was misdocumented:** X = curl toward/across the palm (opposition direction), Z = spread toward/away from the index. **Fixed** unnatural "thumb points down" fist: metacarpal now gets half the curl (30/60/60) |
| Extremes | Grip > ~80° pushes fingertips into the palm (low-poly mesh, equal joint distribution) – documented |

## 5. Foot IK (v1 limits, documented)

No heel/toe roll pivots or roll slider (foot pivots at the ankle); no knee-pop softening near full extension; moving `CTRL_Root` moves the feet. Fine for v1; heel/toe roll is the first upgrade worth doing.

## 6. Other fixes

- `CTRL_Hips` location locked: translating it moved the deform upper body away from the spine/head controls. Body translation is `CTRL_Torso`'s job.
- IK pole angles solved with a more robust search.
- Docs: precision claims corrected (rest pose matches within 0.05° – float32 level – not "0.0000°"), "spread/opposition" wording, weapon/camera behaviour, Unity assumptions marked as assumptions.

## Open – needs the Unity project

1. Import `Exports/Example_FPS_Ready.fbx` as Humanoid (*Copy From Other Avatar*) and check the pose.
2. Compare `AnimCamera` rest with the current neutral FPS camera.
3. Confirm the right-hand weapon socket convention and values.
4. Implement camera offset / cutscene ownership (RIG_PLAN §4), including the root-motion rule.
