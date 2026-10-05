# FPS Animation Rig

Artist-friendly full-body FPS animation rig in Blender for the Mixamo-based `LowPolyMale` character, exporting Unity Humanoid clips.

- `Blender/FPS_Rig.blend` – the rig, with start poses and the **FPS Rig** sidebar panel (N → FPS Rig). Open it and animate.
- `Docs/ANIMATOR_GUIDE.md` – how to animate and export (Norwegian, step by step).
- `Docs/UNITY_INTEGRATION.md` – importing clips, layers, weapon socket, events, camera offset.
- `Docs/RIG_PLAN.md` / `Docs/RIG_REVIEW.md` – source inspection, rig design and review notes.
- `Exports/` – exported FBX clips (skeleton only). `Pistol_Draw.fbx` is the test animation.
- `Source/LowPolyMale_Rigged.fbx` – untouched reference character.
- `Blender/scripts/` – one-time rig build script and the FPS Rig panel / export tools (also embedded in the .blend).
