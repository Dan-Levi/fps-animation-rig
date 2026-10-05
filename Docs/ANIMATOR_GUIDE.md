# Animatørguide – FPS-riggen

Fil: `Blender/FPS_Rig.blend`. Laget og testet i Blender 5.0, så bruk 5.0 eller nyere.

![Startposer](images/start_poses.png)

---

## 0. Første gang du åpner filen

1. Åpne `Blender/FPS_Rig.blend`. Figuren står i **Unarmed_Idle**, og ingen våpen er synlige.
2. Viser Blender en gul linje øverst om at Python-skript er blokkert, trykker du **Allow Execution**. Da får du verktøypanelet **FPS Rig**.
   - Gikk den linja forbi: åpne **Scripting**-fanen, velg `fps_rig_tools.py` i tekstredigereren og trykk **Run Script**.
   - Vil du slippe dette hver gang: **Edit → Preferences → Save & Load → Auto Run Python Scripts**.
3. I 3D-vinduet trykker du **N** og velger fanen **FPS Rig** til høyre.
4. Velg riggen og gå til **Pose Mode** (Ctrl+Tab).

Riggen virker fint uten panelet. Panelet gir bare to snarveier: bytte Follow uten hopp, og eksport.

---

## 1. Startposene (Actions)

Hver animasjon er en **Action** i Blender og blir én FBX-fil i Unity. Disse følger med:

| Action | Hva | Våpen å vise | Loop |
|---|---|---|---|
| `Unarmed_Idle` | Står avslappet med armene ned og puster | – | 60 frames |
| `Guard_Idle` | Knyttnever oppe, lett sving og pust | – | 60 frames |
| `Melee_Bat_Idle` | Balltre med to hender ved skulderen | `REF_Bat` | 60 frames |
| `Melee_Crowbar_Idle` | Brekkjern i høyre hånd, venstre hånd avslappet | `REF_Crowbar` | 60 frames |
| `Pistol_Idle_Hip` | Pistol med to hender i hofteposisjon, sikter mot midten av skjermen | `REF_Pistol` | 60 frames |
| `Pistol_Draw` | **Testanimasjon:** fra idle trekkes pistolen og ender i `Pistol_Idle_Hip` | `REF_Pistol` | nei, 24 frames |
| `Example_FPS_Ready` | Rifle klar | `REF_Rifle` | nei |

![Pistol_Draw](images/pistol_draw.png)

**Vise våpen:** I Outliner (øverst til høyre) åpner du samlingen **Weapon References** og klikker øye-ikonet på våpenet du vil se. Ha bare ett synlig om gangen. Våpenene eksporteres aldri; de er bare referanser i Blender.

---

## 2. Lage en ny animasjon

1. Bytt et av vinduene nederst til **Dope Sheet** og sett modusen til **Action Editor**.
2. Velg startposen som ligner mest i Action-menyen (f.eks. `Pistol_Idle_Hip` for et pistolskudd).
3. Trykk **duplikat-knappen** ved siden av navnet. Du får en kopi som `Pistol_Idle_Hip.001`.
4. Gi den nytt navn, f.eks. `Pistol_Fire_Hip`. **Navnet blir klippnavnet i Unity.**
5. Trykk **skjold-ikonet (Fake User)**, så Blender aldri sletter den.
6. Lager du en animasjon som spilles én gang, altså ikke en loop: i **Graph Editor** velger du alle kanaler (A) og trykker **Shift+E → Clear Cyclic (F-Modifier)**. Idle-posene loopes i Blender, men kopien skal ikke det.
7. Sett lengden: i Action Editor trykker du **N**, åpner fanen **Action** og huker av **Manual Frame Range**, f.eks. 1–20. Eksporten bruker dette området.
8. Animer kontrollene og sett nøkler med **I**. Hold deg til 30 fps.
9. Sjekk resultatet i **FPS-visning** (Numpad 0) og i full kropp: velg `External_View` og trykk Ctrl+Numpad 0, eller roter fritt i vinduet.
10. Eksporter (kapittel 7) og lagre `.blend`-filen.

**Reset av en pose:** velg kontrollene og trykk **Alt+G** (posisjon) og **Alt+R** (rotasjon).

---

## 3. Kontrollene

Bare de fargede formene er ment å animeres. Gul er kroppen, blå er venstre, rød er høyre, grønn er fingrene, oransje er våpenet og lilla er kameraet.

| Hva du vil | Ta tak i |
|---|---|
| Flytte hele karakteren | `CTRL_Root` (stor sirkel på gulvet). La den stå i origo for klipp som skal stå på stedet |
| Flytte kroppen eller gå ned i huk | `CTRL_Torso` (boksen ved hoftene). Flytt ned, og føttene blir stående |
| Vippe eller svinge bekkenet | `CTRL_Hips` (bare rotasjon) |
| Bøye eller vri overkroppen | `CTRL_Spine`, `CTRL_Chest`, `CTRL_UpperChest` |
| Se rundt | `CTRL_Neck`, `CTRL_Head` |
| Trekke på skuldrene | `CTRL_Shoulder.L/R` (roter X) |
| Flytte våpenet og høyre hånd som holder det | `CTRL_Weapon` (oransje boks langs løpet) |
| Plassere hendene | `CTRL_Hand_IK.L/R` (boks rundt hånden) |
| Rette albuene | `CTRL_Elbow_Pole.L/R` (diamanter bak albuene) |
| Plassere føttene | `CTRL_Foot_IK.L/R` (plate under foten, roterer rundt ankelen) |
| Bøye tærne | `CTRL_Toe.L/R` |
| Rette knærne | `CTRL_Knee_Pole.L/R` (diamanter foran knærne) |
| Animasjonskamera | `CTRL_Camera` (kamera-ikon ved øynene) |

Verdiene i sidepanelet (N → Item) er ekte meter og grader. Posisjonene er målt i forhold til der kontrollen «hører hjemme», så tallene kan se store ut, f.eks. −1.5 m på en hånd som følger våpenet. Det er normalt.

### Fingre (grønne)

| Kontroll | Roter X | Roter Z |
|---|---|---|
| `CTRL_Grip.L/R` (streken over knokene) | Knyttneve: bøyer alle fire fingre | Vifte: +Z sprer fingrene, −Z samler dem. Likt på begge hender |
| `CTRL_Index/Middle/Ring/Pinky.L/R` | Bøyer den fingeren (alle tre ledd) | Flytter fingeren sidelengs ved knoken |
| `CTRL_Thumb.L/R` | Bøyer tommelen inn mot og over håndflaten | Svinger tommelen mot eller bort fra pekefingeren |

- Positiv X lukker og negativ X åpner, på begge hender.
- Alt legges sammen. Grip X 65 og Index X −45 gir for eksempel en avtrekkerfinger som er nesten rett mens resten holder grepet.
- Finjustering: slå på bein-samlingen **Finger Detail** (Armature-egenskaper → Bone Collections). Den gir én liten sirkel per ledd.
- Grip over omtrent 80° presser fingertuppene inn i håndflaten på denne low-poly-modellen.

---

## 4. Follow-sliderne, og hvorfor hånden kan hoppe

Velg kontrollen. Slideren står i **FPS Rig**-panelet og i N → Item → Properties.

| Kontroll | Slider | 0 | 1 |
|---|---|---|---|
| `CTRL_Hand_IK.R` | Follow Weapon | Høyre hånd er fri | Høyre hånd bæres av `CTRL_Weapon` |
| `CTRL_Hand_IK.L` | Follow Weapon | Venstre hånd er fri | Venstre hånd blir på våpenet (slik det sitter i høyre hånd) |
| `CTRL_Weapon` | Follow Chest | Våpenet står i ro når kroppen beveger seg | Våpenet følger overkroppen |
| `CTRL_Camera` | Follow Head | Kameraet beveger seg bare når du animerer det | Kameraet følger hodet |

**Hvorfor hånden hopper når du drar slideren:** Hånden lagrer posisjonen sin *i forhold til* det den følger. Bytter du fra «våpenet» til «rommet», brukes de samme tallene fra et nytt utgangspunkt, og hånden havner et annet sted. Riggen er ikke ødelagt.

**Løsningen:** bruk knappen **Switch Follow (keep pose)** i FPS Rig-panelet:
1. Gå til framen der byttet skal skje, f.eks. der venstre hånd slipper våpenet for å ta et nytt magasin.
2. Velg kontrollen, f.eks. `CTRL_Hand_IK.L`.
3. Trykk **Switch Follow (keep pose)**. Slideren bytter, hånden blir stående, og alt nøkles automatisk: den gamle verdien på framen før og den nye på denne framen.

Startposene har sliderne ferdig nøklet, så hver Action husker sine egne verdier.

---

## 5. Våpen og verktøy

Våpenet sitter **alltid i høyre hånd** med et fast grep, på samme måte som det festes til høyre hånd i Unity. Det du ser i Blender, er det du får i spillet.

- **`WPN_Attach`** (tom med piler) er festepunktet. Origo er grepspunktet, Z-pila peker langs løpet (eller den «farlige enden»), og Y-pila peker opp.
- **Ditt eget våpen:**
  1. File → Import (FBX/OBJ).
  2. Velg våpenet, Shift-klikk `WPN_Attach`, og trykk **Ctrl+P → Object (Keep Transform)**.
  3. Flytt og roter *våpenet* (ikke tomen) til grepet ligger i origo for `WPN_Attach` og løpet peker langs Z-pila.
  4. Skjul plassholderen.
- **Animere:** flytt og roter `CTRL_Weapon`. Høyre hånd følger, og våpenet følger høyre hånd.
- **Høyre Follow Weapon = 0:** animer `CTRL_Hand_IK.R` direkte (fint for nærkampslag). Våpenet følger fortsatt hånden, men `CTRL_Weapon` gjør da ingenting.
- **Uten våpen:** Follow Weapon = 0 på begge hender, og skjul våpenet.
- Ikke støttet i v1: å gi våpenet over til venstre hånd.

---

## 6. Oppskrifter

**Bruk alltid `FPS_View` (Numpad 0) når du lager FPS-poser.** Korset midt i kamerabildet er der spillets siktekors er.

### Trekke våpen (se `Pistol_Draw`)
1. Start fra posen til `Unarmed_Idle`: dupliser `Pistol_Draw` eller `Unarmed_Idle` og fjern loopen (Shift+E).
2. Sett **Follow Weapon = 0 på høyre hånd** for hele klippet, og animer høyre hånd til holsteret og opp.
3. Legg en markør der våpenet skal dukke opp, f.eks. når hånden er ved hofta:
   - I Action Editor slår du på **Show Pose Markers**. Den ligger i View-menyen eller Marker-menyen, avhengig av Blender-versjonen.
   - Trykk **M** på framen, og gi markøren navnet `WeaponShow` (F2).
4. Venstre hånd kommer opp. På framen der den griper, trykker du **Switch Follow** på `CTRL_Hand_IK.L` (0 → 1).
5. Avslutt i nøyaktig samme pose som idle-posen klippet skal gå over i, f.eks. `Pistol_Idle_Hip`.

### Holstre
- Lag trekkanimasjonen baklengs: dupliser den, velg alle nøkler i Dope Sheet, sett tidslinjen midt i klippet, og velg **Key → Mirror → By Times Over Current Frame**. Juster deretter timingen.
- Markøren heter `WeaponHide`, og settes der våpenet er tilbake i hofta.

### Sikte fra hofta og ADS (ironsight/kikkert)
- Lag posene **i vater** (se rett fram). Spillet bøyer ryggraden i kode når spilleren ser opp eller ned.
- **Hofte:** løpet skal peke mot korset i `FPS_View`, og våpenet synes nede til høyre.
- **ADS:** flytt `CTRL_Weapon` til bakre og fremre sikte (eller kikkerten) ligger rett over korset i `FPS_View`. Kameraet står stille, så du flytter våpenet til øyet og ikke øyet til våpenet.

### Skudd og rekyl
- 1–2 frames: våpenet sparkes litt bakover og opp med `CTRL_Weapon`. Deretter 6–10 frames tilbake til utgangsposen.
- Valgfritt: en liten rotasjon på `CTRL_Camera` (1–2°) gir kamerarykk. Den legges oppå spillerens kamera i Unity.

### Lading
- Når venstre hånd slipper våpenet: **Switch Follow** (1 → 0). Når den griper igjen: **Switch Follow** (0 → 1).

### Nærkamp (balltre eller brekkjern)
- Balltre: begge hender følger. Animer `CTRL_Weapon` gjennom slaget og vri overkroppen (`CTRL_Torso`, `CTRL_Chest`).
- Brekkjern: venstre hånd er fri (Follow 0).
- Treffet: et lite kamerarykk på `CTRL_Camera` er valgfritt.

### Interaksjon: vri om nøkkel
- Vis `REF_Key`. Høyre Follow Weapon = 1 og venstre = 0.
- Roter `CTRL_Weapon` rundt sin egen Y-akse, som går langs nøkkelbladet. Bøy fingrene med `CTRL_Thumb.R` og `CTRL_Index.R`.

### Kamera i animasjon
- Vanlige klipp: ikke rør `CTRL_Camera`. Da får spilleren full kontroll.
- Kamerarykk (treff, rekyl) og cutscenes: animer `CTRL_Camera`. Bruk **Follow Head** = 1 når kameraet skal følge hodet, f.eks. når man blir slått ned.
- Om et klipp *styrer* kameraet eller bare *legger til* bevegelse, bestemmes i Unity.
- `FPS_View` viser det nøytrale spillkameraet pluss det du animerer. Det viser ikke huk-høyden eller musebevegelsen fra spillet.

### Overkroppsklipp
- Klipp som skal spilles oppå Mixamo-gange (våpenposer, skudd, lading, trekk): **ikke flytt `CTRL_Torso` eller `CTRL_Root`.** Bare overkropp, armer og hode tas med i Unity.

---

## 7. Eksport til Unity

**FPS Rig-panelet → Export this Action** (eller **Export all Actions**).

Dette skjer når du trykker:
1. Den aktive Actionen spilles av frame for frame i Action-ens frame-område, med 30 fps.
2. Mixamo-skjelettet (65 bein) og `AnimCamera` bakes, altså hver frame lagres som ren beinbevegelse.
3. Alt det andre blir igjen i Blender: kontroller, våpen, mesh og kameraer.
4. Resultatet skrives til **`Exports/<Action-navn>.fbx`**: **kun skjelett, uten skin**, akkurat som «Without Skin» fra Mixamo.
5. **Export all Actions** gjør det samme for alle Actions i filen og lager én FBX per Action.

**I Unity** gjør du det samme som med Mixamo-animasjoner:
1. Dra FBX-filen inn i prosjektet.
2. Under **Rig** velger du Animation Type **Humanoid**, Avatar Definition **Copy From Other Avatar** og den eksisterende Mixamo-avataren. Trykk **Apply**.
3. Under **Animation** heter klippet det samme som Actionen. Huk av **Loop Time** for idle-klippene.
4. Markøren `WeaponShow`/`WeaponHide` blir ikke med automatisk. Legg den inn som en **Animation Event** på samme frame (se `Docs/UNITY_INTEGRATION.md`).

**Manuell eksport** (uten panelet): velg bare riggen og gå til File → Export → FBX med disse innstillingene: Selected Objects, Object Types = Armature, **Apply Scalings = FBX Units Scale**, Forward −Z, Up Y, **Only Deform Bones** på, **Add Leaf Bones** av, Bake Animation på, NLA Strips av, All Actions av, Simplify 0.

---

## 8. Begrensninger og tips

- **Foten roterer rundt ankelen.** Det finnes ikke hæl- eller tåpivot. For å løfte hælen roterer du foten og flytter den ned. For tåhev bøyer du også `CTRL_Toe`.
- **Helt rette bein** kan få knærne til å «poppe». Behold en liten bøy.
- **Flytter du `CTRL_Root`, flytter føttene seg også.** Bruk `CTRL_Torso` for å flytte kroppen med føttene på plass.
- **Ikke flytt, gi nytt navn til eller endre forelder på bein i Edit Mode.** Mixamo-skjelettet må være identisk for Unity.
- **La de skjulte bein-samlingene `Deform (Mixamo)` og `Mechanism` være skjult.**
- **Riggen bygges fra kilde-FBX-en med `Blender/scripts/build_fps_rig.py`.** Det trengs bare hvis selve riggen skal endres. Animasjonene dine i en eksisterende fil blir ikke med automatisk.
