# Animator Guide – FPS Rig

File: `Blender/FPS_Rig.blend` – built and tested with Blender 5.0; use 5.0 or newer.

![External view](images/external_view.png)
![FPS view](images/fps_view.png)

## Start a new animation

1. Open `Blender/FPS_Rig.blend`. It opens on the Action **Example_FPS_Ready** (rifle ready pose).
2. Select the rig, go to **Pose Mode**.
3. In the **Dope Sheet → Action Editor**, click the *duplicate* button next to the Action name to start from the ready pose, or **New** to start from scratch. Give it the clip name you want in Unity (e.g. `Rifle_Reload`).
4. Click the shield icon (Fake User) so Blender never discards it.
5. Set the clip length with **Manual Frame Range** (Action Editor sidebar → Action). Export uses the Action's frame range. 30 fps.

## Controls

Only the coloured shapes are meant to be animated. Yellow = body, blue = left, red = right, green = fingers, orange = weapon, purple = camera.

| What you want | Grab |
|---|---|
| Move whole character | `CTRL_Root` (big circle on the floor) – keep at origin for in-place clips |
| Move / crouch the body | `CTRL_Torso` (box at the hips) – move down, feet stay planted |
| Tilt / swing pelvis | `CTRL_Hips` – rotation only |
| Bend / twist upper body | `CTRL_Spine`, `CTRL_Chest`, `CTRL_UpperChest` |
| Look around | `CTRL_Neck`, `CTRL_Head` |
| Shrug | `CTRL_Shoulder.L/R` |
| Move the weapon (and the right hand holding it) | `CTRL_Weapon` |
| Place hands | `CTRL_Hand_IK.L/R` (box around the hand) |
| Aim elbows | `CTRL_Elbow_Pole.L/R` (diamonds behind the elbows) |
| Place feet | `CTRL_Foot_IK.L/R` (flat plate under the foot; pivots at the ankle) |
| Bend toes | `CTRL_Toe.L/R` |
| Aim knees | `CTRL_Knee_Pole.L/R` (diamonds in front of the knees) |
| Animation camera | `CTRL_Camera` (camera-shaped icon at the eyes) |

Note: rotating `CTRL_Hips` shifts the base of the spine slightly, so the upper-body shapes can sit a centimetre or two off the mesh during big pelvis rotations. That is expected.

### Fingers (green)

| Control | Rotate X | Rotate Z |
|---|---|---|
| `CTRL_Grip.L/R` (bar above the knuckles) | fist: curls all 4 fingers | fan: +Z spreads the fingers apart, −Z squeezes them (same on both hands) |
| `CTRL_Index/Middle/Ring/Pinky.L/R` | curl that finger (all 3 joints equally) | move that finger sideways at the knuckle |
| `CTRL_Thumb.L/R` | curl the thumb toward / across the palm | swing the thumb toward / away from the index finger |

- Positive X closes, negative X opens, on both hands.
- Per-finger Z is mirrored between hands (the same number moves the left and right finger in opposite directions) – just rotate the control the way you want the finger to go, or use the Grip fan for a symmetric spread.
- Grip, finger curl and the detail controls add together. Example: Grip X 60 + Index X −45 = trigger finger mostly straight while the others hold the grip.
- For fine detail, show the **Finger Detail** bone collection: one small circle per joint, added on top of everything else.
- Very large curls (Grip > ~80°) push fingertips into the palm on this low-poly mesh.

### Sliders (select the control, see **N panel → Item → Properties**)

| Control | Slider | 0 | 1 (default) |
|---|---|---|---|
| `CTRL_Hand_IK.R` | Follow Weapon | right hand is free | right hand is carried by `CTRL_Weapon` |
| `CTRL_Hand_IK.L` | Follow Weapon | left hand is free | left hand stays on the weapon (as held in the right hand) |
| `CTRL_Weapon` | Follow Chest | weapon stays in place when the body moves | weapon moves with the upper body |
| `CTRL_Camera` | Follow Head | camera only moves when you animate it (default 0) | camera also follows the head |

Set these once per Action. They can be keyed, but switching mid-animation makes the hand/weapon/camera jump unless you counter-animate it.

## Weapons and tools

The weapon always sits in the **right hand**, at a fixed grip – the same way a right-hand socket attaches it in Unity (assumed runtime convention; see Docs/RIG_PLAN.md §5). What you see in Blender is what Unity shows.

- `REF_Weapon` is a placeholder rifle, parented to the empty **`WPN_Attach`** (origin = pistol-grip point, Z arrow = barrel, Y arrow = up).
- Your own weapon/tool: import it, select it, then Shift-select `WPN_Attach` and **Ctrl+P → Object (Keep Transform)**. Move/rotate the weapon (not the empty) until its grip sits at the empty's origin and the barrel points along the Z arrow. Hide the placeholder.
- Animate the weapon with `CTRL_Weapon`; the right hand follows it and the weapon follows the right hand.
- Right hand **Follow Weapon** = 0 (e.g. melee swings animated from the hand): animate `CTRL_Hand_IK.R` directly – the weapon still follows the hand; `CTRL_Weapon` then has no effect.
- Unarmed or interaction clips: set **Follow Weapon** to 0 on both hands and hide the weapon.
- Not supported in v1: passing the weapon to the left hand or holding it only in the left hand.
- The weapon is not exported. In Unity the left hand may sit a few millimetres off the weapon after Humanoid retargeting; runtime left-hand IK usually takes care of that.

## Camera

- `FPS_View` (scene camera) looks through the animation camera: Numpad 0. `External_View` is a full-body camera (select it, Ctrl+Numpad 0).
- `FPS_View` shows the *neutral* gameplay camera plus whatever you animate on `CTRL_Camera`. It does not follow player look or the game's crouch height.
- Normal clips: leave `CTRL_Camera` alone. The exported camera then has zero offset and the player keeps full camera control.
- Animate it only for deliberate camera moments: melee impact shake, recoil kick, takedowns, knockdown/get-up, scripted interactions. In-game this is added on top of the player camera.
- Cutscenes where the animation takes over the camera: animate `CTRL_Camera` freely; use **Follow Head** = 1 when the camera should ride the head (e.g. knockdown). Whether a clip *owns* the camera or only *offsets* it is decided in Unity, not in Blender.
- The camera moves with `CTRL_Root`. If a camera-owned clip travels (character moves across the floor), tell the Unity side – root motion and the camera curve must not both move the camera.
- Tip: enable **Backface Culling** in the viewport shading options to avoid seeing the inside of the head in FPS view.

## Feet – current limits

- The foot control rotates around the **ankle**. There is no heel or toe-tip pivot and no foot-roll slider: for a heel lift, rotate the foot and move it down; for tip-toes, also bend `CTRL_Toe`.
- Raising the body until the legs are fully straight can make the knees pop. Keep a slight bend.
- Moving `CTRL_Root` moves the feet too; to keep feet planted while the body moves, use `CTRL_Torso`.

## Export to Unity

1. Make sure the Action you want is active on the rig.
2. **Scripting** workspace → Text Editor → select `export_action_to_unity.py` → **Run Script** (Alt+P).
3. The file appears at `Exports/<ActionName>.fbx`: the Mixamo skeleton + `AnimCamera`, baked, no control bones.

Manual alternative: select only the rig, **File → Export → FBX** with: Selected Objects, Object Types = Armature, **Apply Scalings = All Local**, Forward −Z, Up Y, **Only Deform Bones** on, **Add Leaf Bones** off, Bake Animation on, NLA Strips off, All Actions off, Simplify 0. (All Local keeps the file in centimetres like the source character; other scaling options put a 0.01 scale on the root in Unity.)

### Unity import

- Rig: **Humanoid**, Avatar Definition: **Copy From Other Avatar** → the existing Mixamo character avatar.
- Animation tab: the clip is named after the Action. Check Start/End frames match the Action range.
- Camera and weapon socket setup for programmers: Docs/RIG_PLAN.md §4 and §5.

## Reset / tips

- Reset a pose: select controls, **Alt+G / Alt+R** (clear location/rotation).
- Don't move, rename or re-parent bones in Edit Mode – the Mixamo skeleton must stay identical for Unity.
- Hidden bone collections **Deform (Mixamo)** and **Mechanism** are rig internals; leave them hidden.
- Rebuilding the rig from the source FBX: `Blender/scripts/build_fps_rig.py` (only needed if the rig itself must change; Actions in an existing file are not carried over automatically).
