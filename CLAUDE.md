# CLAUDE.md

## Project purpose

Build a clean, artist-friendly **full-body FPS animation rig in Blender** that exports reliably to Unity.

The source character is:

`Source/LowPolyMale_Rigged.fbx`

The character uses a standard **Mixamo humanoid skeleton**. The final exported animations must remain compatible with that skeleton and Unity Humanoid.

This repository is focused only on the animation-rigging toolchain.

## Primary goals

Create one Blender working rig that is comfortable to animate manually for:

- first-person full-body animation;
- third-person / remote-player presentation;
- ranged weapons;
- melee weapons;
- tools;
- idle / equip / unequip;
- fire / recoil;
- reload;
- attacks;
- interactions;
- special animation-driven camera moments.

The rig must be easy for a non-expert Blender animator to understand and use.

## Core design rule

Separate:

1. **Deform/export skeleton** — the original Mixamo skeleton used by Unity.
2. **Animator controls** — convenient Blender-only controls.

Animator controls must not require changing the production skeleton hierarchy, rest pose, bone names, or skin weights.

Animations should be baked to the deform skeleton for export.

## Required controls

The working rig should provide clear controls for the important parts of the character:

- Root / global
- Hips / pelvis
- Torso / chest
- Head
- Left and right hand IK
- Left and right elbow pole controls
- Left and right foot IK
- Left and right knee pole controls
- Practical finger controls
- Weapon / tool reference or socket control
- Camera control / camera bone support

Controls should be clearly named, visually distinct and easy to select.

Avoid making the animator manipulate raw deform bones unless necessary.

## Hands and fingers

Finger animation must be significantly easier than selecting every Mixamo finger bone manually.

Prefer simple animator-facing controls such as:

- whole-hand grip / curl;
- individual finger curl;
- thumb curl;
- thumb spread;
- optional per-finger fine adjustment.

The result must still bake correctly to the original Mixamo finger bones.

## Feet and lower body

The rig should support planted feet.

Use animator-friendly foot IK and knee pole controls so that lowering the hips produces a natural crouch instead of sending the feet through the ground.

Do not permanently alter the Mixamo deform hierarchy to achieve this.

## Camera

The normal Unity FPS camera is player-controlled.

The Blender rig should additionally support an **animation camera bone/control** so authored animation can optionally add camera movement for moments such as:

- heavy melee impact;
- recoil;
- takedowns;
- knockdown / get-up;
- scripted interactions.

The camera control must not imply that animation always owns the gameplay camera.

The intended Unity model is:

`player look / gameplay camera + optional animation-driven camera offset`

Before finalizing camera placement, inspect the existing Unity project and reproduce the current neutral FPS camera position/orientation because that setup is already considered correct.

## Blender workflow target

The intended animator workflow should be approximately:

1. Open the main rig .blend.
2. Choose or create an Action.
3. Add a weapon/tool reference if needed.
4. Pose the character using obvious controls.
5. Animate hands, body, fingers, feet and optional camera.
6. Preview from FPS camera and external full-body view.
7. Bake/export the selected Action to the Mixamo deform skeleton.
8. Import the FBX animation into Unity Humanoid.

The animator should not have to coordinate multiple hidden Actions or run several helper scripts just to edit one animation.

## Unity compatibility

Exports must be suitable for Unity Humanoid and the existing Mixamo Avatar.

Preserve:

- bone names;
- hierarchy;
- rest pose;
- body proportions;
- skin weights unless a deliberate weight-fix task is being performed.

Animation exports should contain the deform skeleton and animation data needed by Unity, not Blender-only control objects.

Target convention:

- 30 FPS unless explicitly changed;
- FBX suitable for Unity;
- no unnecessary leaf bones;
- no Blender control bones exported as part of the production humanoid.

## Simplicity requirement

This rig is an animator tool, not a scripting experiment.

Prefer:

- Blender-native constraints;
- clear control bones / custom shapes;
- conventional IK/FK setup;
- simple drivers only when they materially improve usability.

Avoid unnecessary Python-based runtime authoring systems, generated validation clutter, or workflows that require scripts for ordinary animation editing.

Scripts may be used for one-time rig construction, baking, or export automation if useful, but the finished rig itself should be comfortably usable through Blender's normal UI.

## Source safety

Treat `Source/LowPolyMale_Rigged.fbx` as the reference source.

Do not overwrite it.

When experimenting with rig construction or weights, work in separate Blender files and preserve recoverable versions.

## Repository direction

Expected structure:

```text
Source/      source/reference FBX assets
Blender/     working and production .blend files
Exports/     exported animation FBXs
Docs/        concise rig and workflow documentation
```

Git LFS is used for `*.fbx` and `*.blend`.

## First implementation phase

Before building the production rig:

1. Inspect the source FBX skeleton, mesh, weights and axes.
2. Confirm the Mixamo bone hierarchy and orientation.
3. Inspect the current Unity FPS camera placement in the existing Unity project.
4. Define the control-rig hierarchy.
5. Prototype hand IK, foot IK, finger controls and camera control.
6. Verify that baking back to the untouched Mixamo deform skeleton imports correctly in Unity.
7. Only then build the clean production .blend.

## Success criteria

The rig is successful when an animator can comfortably create a new weapon animation in Blender without needing to understand the underlying technical rig, while the resulting animation still works on the original Mixamo-based Unity character.
