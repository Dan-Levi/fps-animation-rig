# FPS Animation Rig

Artist-friendly full-body FPS animation rig in Blender for a Mixamo-rigged character (currently `LowPolyGuy`), exporting Unity Humanoid clips.

- `Blender/FPS_Rig.blend` – the rig, with start poses and the **FPS Rig** sidebar panel (N → FPS Rig). Open it and animate; beginners start with the built-in **FPS Rig – Tutorial** panel.
- `Docs/ANIMATOR_GUIDE.md` – how to animate, rig new weapons (3ds Max → Blender) and export (Norwegian, step by step).
- `Docs/UNITY_INTEGRATION.md` – importing clips, layers, weapon socket, events, camera offset.
- `Docs/RIG_PLAN.md` / `Docs/RIG_REVIEW.md` – source inspection, rig design and review notes.
- `Exports/` – exported FBX clips (character skeleton only); `Exports/Weapons/<Weapon>/` – weapon models and weapon clips (Generic).
- `Source/Characters/` – the character the rig is built from (Mixamo rig, any size: the build scales it to 1.75 m); `Source/Weapons/`, `Source/Animations/` – weapon models and ready-made clips. `Source/LowPolyMale_Rigged.fbx` – the first character, kept for reference.
- `Exports/Character/` – the skinned character for the Unity Humanoid avatar.
- `Blender/scripts/` – one-time rig build script and the FPS Rig panel / export tools (also embedded in the .blend).
