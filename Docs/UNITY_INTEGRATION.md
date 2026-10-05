# Unity-integrasjon

For den som setter opp klippene i Unity. Animatørdelen står i `ANIMATOR_GUIDE.md`.

## 1. Import av et klipp

1. Legg `Exports/<Navn>.fbx` i prosjektet. Filen har bare skjelett, uten skin, i meter (66 bein: Mixamo + `AnimCamera`).
2. Under **Rig** velger du Animation Type **Humanoid**, Avatar Definition **Copy From Other Avatar** og den eksisterende Mixamo-avataren. Trykk Apply. Dette er samme arbeidsflyt som for Mixamo-klipp.
3. Under **Animation**:
   - Klippet heter det samme som Blender-Actionen. Sjekk at Start og End stemmer med lengden.
   - Huk av **Loop Time** og **Loop Pose** for `*_Idle`-klippene.
   - Klipp som står på stedet: huk av **Bake Into Pose** for Root Transform Rotation, Y og XZ.
4. Skal du hente kamera-offset fra klippet: åpne **Mask → Transform** og ta med `Armature/AnimCamera`. Se §5.

**Første test (punkt 6):** importer `Pistol_Draw.fbx` og `Pistol_Idle_Hip.fbx`, og spill dem på figuren. Den skal ikke sveve, synke eller ha feil skala.

## 2. Lag i Animatoren (anbefalt oppsett)

| Lag | Innhold | Maske | Blending |
|---|---|---|---|
| Base | Mixamo-gange (idle, gå, løpe) og `Unarmed_Idle` | full kropp | – |
| UpperBody | Våpen-idle, trekk, holster, skudd, lading, ADS, nærkamp | Spine, Chest, UpperChest, armer, hender og fingre. Hodet er valgfritt | Override, vekt 1 når et våpen er aktivt |
| (valgfritt) Camera | Klipp med kamera-offset | bare `AnimCamera` | lest av kode (§5) |

Overkroppsklippene er laget uten bevegelse i torso og rot, slik at de passer oppå hvilken som helst gange.

## 3. Våpenbytte (tast 1/2, høyreklikk)

Eksempel på flyt for UpperBody-laget:

```
[Ubevæpnet]  --1-->  Pistol_Draw  --(ferdig)-->  Pistol_Idle_Hip  <--> Pistol_ADS (høyreklikk holdes)
[Pistol]     --2-->  Pistol_Holster  --(ferdig)-->  Shotgun_Draw  --> Shotgun_Idle_Hip ...
```

- **Vise og skjule våpen:** legg inn Animation Events i klippets import-innstillinger (Animation → Events) på framen fra Blender-markøren:
  - `Pistol_Draw`: `WeaponShow` på frame 8 av 24. Det tilsvarer normalisert tid (8−1)/(24−1) ≈ 0.304, eller 0.233 s.
  - Holster-klipp: `WeaponHide` når hånden er tilbake ved hofta.
- **Våpenet festes til en socket under `mixamorig:RightHand`:**
  - localPosition (m): **(0.0000, 0.0660, 0.0250)**
  - localRotation (x, y, z, w): **(−0.48823, 0.62694, 0.36381, 0.48602)**, som tilsvarer Euler ≈ (291.45, 135.96, 315.00)
  - Socketens akser er +Z langs løpet og +Y opp, med origo i pistolgrepet. Et våpen-prefab med +Z fram og pivot i grepet trenger da ingen ekstra rotasjon.
  - Verdiene er regnet ut fra riggen og sjekket mot FBX-en. Kontroller én gang med øyet at pistolen sitter i hånden mens `Pistol_Idle_Hip` spilles.
- **ADS** er et eget klipp der siktet ligger på kameraets akse. I tillegg kan zoom/FOV styres i kode.
- **Riggede våpen** (slide, magasin osv.) har sin egen prefab og Animator. Se §7.

## 4. Se opp og ned (pitch)

Ryggraden bøyes i kode etter kamerapitch, f.eks. i LateUpdate eller med en Animation Rigging Multi-Rotation på Spine, Chest og UpperChest.

- Posene er laget i vater (pitch 0). Siktet ved ADS stemmer nøyaktig ved pitch 0.
- Kameraet roterer rundt øyet, men våpenet roterer rundt ryggraden. Ved store vinkler kan siktet drive litt. Fordel mest av rotasjonen på UpperChest, og legg på en liten korreksjon om det trengs, f.eks. en aim-constraint på våpenet eller hånden.

## 5. AnimCamera (kamera fra animasjon)

- Hvilestilling (lokal, i forhold til karakterens rot): posisjon **(0, 1.645, 0.07) m**, rotasjon identitet. +Z er fram og +Y er opp.
- Figuren trenger en transform på samme sti som i klippene: **`Armature/AnimCamera`** med hvileverdiene over. Lag den under figurens rot, eller importer figuren fra en eksport av riggen.
- **Spill (spilleren styrer kameraet):** `offset = Inverse(rest) * current` og `camera = playerCamera * offset`. Klipp som ikke animerer kameraet gir offset lik identitet.
- **Cutscene (animasjonen styrer kameraet):** `camera = characterRoot * currentLocal`, blandet inn og ut med en vekt.
- **Root motion:** `AnimCamera` inneholder kroppens forflytning, akkurat som Hips gjør. Bruker et kamerastyrt klipp Apply Root Motion, må kameraskriptet trekke fra root motion. Ellers flytter kameraet seg dobbelt. Enklest er å holde slike klipp på stedet.
- Kameraplasseringen må fortsatt sammenlignes med dagens nøytrale FPS-kamera.

## 6. Kjente forskjeller mellom Blender og Unity

- Humanoid-retargeting (muskelgrenser, arm stretch) kan flytte hendene noen millimeter. Støttehånden kan da ligge litt utenfor våpenet. Runtime left-hand IK løser det.
- Blender-markører (`WeaponShow`/`WeaponHide`) blir ikke med i FBX-en og må legges inn som Events manuelt.

## 7. Riggede våpen (slide, avtrekker, magasin)

Hvert riggede våpen eksporteres fra Blender som to slags filer i `Exports/Weapons/<Våpen>/`:

| Fil | Innhold | Import |
|---|---|---|
| `WPN_<Våpen>.fbx` | Modell (delene) + våpenskjelett i hvilestilling | Rig: **Generic**, Avatar Definition: **Create From This Model** |
| `WPN_<Våpen>@<Klipp>.fbx` | Bare våpenets bein, bakt, ett klipp per karakterklipp med samme navn | Rig: **Generic**, Avatar: **Copy From Other Avatar** → avataren fra `WPN_<Våpen>.fbx` |

**Våpenets oppbygning i Unity:**
```
WPN_Pistol            (prefab-rot)
└ WPN_Pistol          (armatur-node, ingen rotasjon/skala)
  └ Pistol_Root       (grepspunktet = socket-origo)
    ├ Pistol_Slide    (+ mesh Pistol_Slide)
    ├ Pistol_Trigger
    ├ Pistol_Magazine
    ├ Pistol_Muzzle   (effektpunkt: munningsflamme)
    └ Pistol_Eject    (effektpunkt: hylser)
```
- Legg prefaben som barn av **`WeaponSocket`** (under `mixamorig:RightHand`, se §3) med **posisjon 0 og rotasjon 0**. Våpenets +Z er løpet, +Y er opp, og origo er grepet. Det er de samme aksene som socketen.
- Prefaben får sin egen **Animator**, med tilstander som heter det samme som karakterklippene: `Pistol_Idle_Hip`, `Pistol_Fire`, `Pistol_Reload` …
- Spill begge samtidig fra kode, for eksempel:
  ```csharp
  characterAnimator.CrossFade("Pistol_Fire", 0.05f, upperBodyLayer);
  weaponAnimator.CrossFade("Pistol_Fire", 0.05f);
  ```
  Klippene er laget på samme tidslinje i Blender, så de holder takt når de startes samtidig.
- **Events** fra Blender-markørene legges inn som Animation Events. Det går greit på karakterklippet, eller på våpenklippet hvis du vil at våpenet skal styre effektene selv:
  - `Fire`: munningsflamme, lyd og hylse ved `Pistol_Muzzle`/`Pistol_Eject`.
  - `MagHide`: skjul magasinet i våpenet, og spawn eventuelt et fysisk magasin som faller.
  - `MagShow`: vis magasinet, som da sitter i venstre hånd.
  - `MagIn`: magasinet sitter. Fyll ammunisjonen.
- Magasinets bevegelse ligger i våpenklippet og er målt i forhold til våpenet. Animasjonen stemmer med venstre hånd i karakterklippet så lenge begge spilles i takt.

